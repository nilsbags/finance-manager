"""CSV import helpers: column mapping, value parsing and dedup hashing.

The UI collects a column mapping from the user (which CSV column means
"date", "amount", etc.) and hands raw rows to :func:`prepare_rows`, which
normalises them into the shape expected by the database layer.
"""

import hashlib
import re
from collections.abc import Callable

import pandas as pd

from database import UNCATEGORIZED

# Matches an unambiguous ISO-8601 style date (YYYY-MM-DD). For these we must
# NOT apply the ``dayfirst`` heuristic, or pandas silently swaps month and day
# (e.g. 2026-02-06 -> 2 June 2026).
_ISO_DATE_RE = re.compile(r"^\s*\d{4}-\d{1,2}-\d{1,2}")

# Logical fields the app understands. ``account`` and ``currency`` may be
# supplied either as a CSV column or as a single constant value entered in the UI.
# ``balance`` is optional and only used to deduce unlisted income (see below).
REQUIRED_FIELDS = ["date", "description", "amount"]
OPTIONAL_FIELDS = ["account", "currency", "balance"]

# Descriptions used for the synthetic rows that capture money movements which the
# statement only reflects in the running balance, not as their own line items.
DEDUCED_INCOME_DESC = "Deduced income (balance change)"
DEDUCED_OUTFLOW_DESC = "Deduced outflow (balance change)"


def make_hash(date: str, amount: float, description: str, account: str) -> str:
    """Build a stable dedup fingerprint for a transaction.

    Two transactions with the same date, amount, description and account are
    treated as the same line item, so re-importing a CSV is idempotent.
    """
    raw = f"{date}|{amount:.2f}|{description.strip().lower()}|{account.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_amount(value: object, decimal_comma: bool = False) -> float | None:
    """Parse a single amount cell into a float, or ``None`` if unparseable.

    Handles thousands separators and the European "comma as decimal point"
    convention (e.g. ``1.234,56`` -> ``1234.56``).
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None

    # Normalise common currency noise.
    text = text.replace("\u00a0", "").replace(" ", "")
    text = text.replace("€", "").replace("$", "").replace("£", "")

    if decimal_comma:
        # 1.234,56 -> 1234.56
        text = text.replace(".", "").replace(",", ".")
    else:
        # 1,234.56 -> 1234.56
        text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value: object, dayfirst: bool = True) -> str | None:
    """Parse a date cell into an ISO ``YYYY-MM-DD`` string, or ``None``.

    ``dayfirst`` only applies to ambiguous formats such as ``31/12/2025``;
    already-ISO values are parsed verbatim so month and day are never swapped.
    """
    text = str(value)
    if _ISO_DATE_RE.match(text):
        ts = pd.to_datetime(text, errors="coerce")
    else:
        ts = pd.to_datetime(value, dayfirst=dayfirst, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


def deduce_balance_rows(ledger: list[dict]) -> list[dict]:
    """Reconstruct money movements that only show up in the running balance.

    Many statements list a card transaction but post incoming transfers,
    interest or fees only as a jump in the running balance. For each row the
    "gap" between the expected balance (``previous_balance + amount``) and the
    actual balance is the size of such an unlisted movement.

    Per-row gaps are noisy because the statement is not strictly ordered, so we
    sum them per account and calendar month (a telescoping sum, which is robust
    to intra-month ordering). Each month with a non-trivial net gap becomes one
    synthetic transaction: positive nets are income, negative nets an outflow.

    ``ledger`` items are dicts with ``order``, ``account``, ``currency``,
    ``date`` (ISO string), ``amount`` and ``balance`` keys.
    """
    if not ledger:
        return []

    df = pd.DataFrame(ledger)
    df["_d"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["_d", "amount", "balance"])
    if df.empty:
        return []

    rows: list[dict] = []
    for (account, currency), group in df.groupby(["account", "currency"], sort=False):
        group = group.sort_values(["_d", "order"]).reset_index(drop=True)
        # gap[i] = balance[i] - (balance[i-1] + amount[i]); the first row has no
        # predecessor, so its NaN gap is ignored (the opening balance is taken
        # as the baseline rather than as income).
        gap = group["balance"] - (group["balance"].shift(1) + group["amount"])
        group = group.assign(_gap=gap, _ym=group["_d"].dt.to_period("M"))

        for ym, month in group.groupby("_ym"):
            net = round(float(month["_gap"].sum(skipna=True)), 2)
            if abs(net) < 0.01:
                continue

            last_date = month["_d"].max().strftime("%Y-%m-%d")
            if net > 0:
                description = DEDUCED_INCOME_DESC
                category, subcategory = "Income", "Other Income"
            else:
                description = DEDUCED_OUTFLOW_DESC
                category, subcategory = "Other", "Misc"

            acct = account or "Unknown"
            rows.append(
                {
                    "date": last_date,
                    "description": description,
                    "amount": net,
                    "account": acct,
                    "currency": currency,
                    "category": category,
                    "subcategory": subcategory,
                    "notes": f"Auto-added from balance reconciliation ({ym}).",
                    "hash": make_hash(last_date, net, description, acct),
                }
            )

    return rows


def latest_balances(
    df: pd.DataFrame,
    mapping: dict,
    *,
    default_account: str = "",
    default_currency: str = "EUR",
    decimal_comma: bool = False,
    dayfirst: bool = True,
) -> list[dict]:
    """Return the most recent running balance per account in the CSV.

    Requires ``mapping["balance"]``. For each ``(account, currency)`` the row
    with the latest date (file order breaks ties) gives the current balance.
    Each result has ``account``, ``currency``, ``balance`` and ``as_of`` keys.
    """
    balance_field = mapping.get("balance")
    if not balance_field:
        return []

    records: list[dict] = []
    for order, (_, raw) in enumerate(df.iterrows()):
        date = parse_date(raw[mapping["date"]], dayfirst=dayfirst)
        balance = parse_amount(raw[balance_field], decimal_comma=decimal_comma)
        if date is None or balance is None:
            continue
        account = (
            str(raw[mapping["account"]]).strip()
            if mapping.get("account")
            else default_account.strip()
        ) or "Unknown"
        currency = (
            str(raw[mapping["currency"]]).strip()
            if mapping.get("currency")
            else default_currency.strip()
        ) or "EUR"
        records.append(
            {"order": order, "account": account, "currency": currency, "date": date, "balance": balance}
        )

    if not records:
        return []

    frame = pd.DataFrame(records)
    frame["_d"] = pd.to_datetime(frame["date"], errors="coerce")
    out: list[dict] = []
    for (account, currency), group in frame.groupby(["account", "currency"], sort=False):
        last = group.sort_values(["_d", "order"]).iloc[-1]
        out.append(
            {
                "account": account,
                "currency": currency,
                "balance": round(float(last["balance"]), 2),
                "as_of": str(last["date"]),
            }
        )
    return out


def prepare_rows(
    df: pd.DataFrame,
    mapping: dict,
    *,
    default_account: str = "",
    default_currency: str = "EUR",
    decimal_comma: bool = False,
    dayfirst: bool = True,
    categorize: Callable[[str], tuple[str, str] | None] | None = None,
    deduce_income: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Convert a raw CSV DataFrame into clean transaction rows.

    ``mapping`` maps logical field name -> CSV column name. ``account`` and
    ``currency`` entries may be ``None`` to fall back to the supplied defaults.
    ``categorize`` is an optional callable ``description -> category`` used to
    auto-apply rules at import time.

    When ``deduce_income`` is set and ``mapping`` includes a ``balance`` column,
    extra synthetic rows are appended for money movements that only appear as
    balance changes (see :func:`deduce_balance_rows`).

    Returns a tuple ``(valid_rows, skipped_rows)`` where skipped rows carry a
    ``_reason`` describing why they could not be parsed.
    """
    valid: list[dict] = []
    skipped: list[dict] = []
    ledger: list[dict] = []
    balance_field = mapping.get("balance") if deduce_income else None

    for order, (_, raw) in enumerate(df.iterrows()):
        date = parse_date(raw[mapping["date"]], dayfirst=dayfirst)
        amount = parse_amount(raw[mapping["amount"]], decimal_comma=decimal_comma)
        description = str(raw[mapping["description"]]).strip()

        account = (
            str(raw[mapping["account"]]).strip()
            if mapping.get("account")
            else default_account.strip()
        )
        currency = (
            str(raw[mapping["currency"]]).strip()
            if mapping.get("currency")
            else default_currency.strip()
        ) or "EUR"

        # Feed the balance ledger from every row with a usable date/amount/balance,
        # independent of the description check below, so the running-balance
        # series stays unbroken even if a line has no description.
        if balance_field:
            balance = parse_amount(raw[balance_field], decimal_comma=decimal_comma)
            if date is not None and amount is not None and balance is not None:
                ledger.append(
                    {
                        "order": order,
                        "account": account or "Unknown",
                        "currency": currency,
                        "date": date,
                        "amount": amount,
                        "balance": balance,
                    }
                )

        # Validate the essentials before committing the row.
        if date is None or amount is None or not description:
            reason = []
            if date is None:
                reason.append("bad date")
            if amount is None:
                reason.append("bad amount")
            if not description:
                reason.append("empty description")
            skipped.append({**raw.to_dict(), "_reason": ", ".join(reason)})
            continue

        category, subcategory = UNCATEGORIZED, ""
        if categorize is not None:
            match = categorize(description)
            if match:
                category, subcategory = match

        valid.append(
            {
                "date": date,
                "description": description,
                "amount": amount,
                "account": account or "Unknown",
                "currency": currency,
                "category": category,
                "subcategory": subcategory,
                "notes": "",
                "hash": make_hash(date, amount, description, account or "Unknown"),
            }
        )

    if balance_field:
        valid.extend(deduce_balance_rows(ledger))

    return valid, skipped
