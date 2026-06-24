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
REQUIRED_FIELDS = ["date", "description", "amount"]
OPTIONAL_FIELDS = ["account", "currency"]


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


def prepare_rows(
    df: pd.DataFrame,
    mapping: dict,
    *,
    default_account: str = "",
    default_currency: str = "EUR",
    decimal_comma: bool = False,
    dayfirst: bool = True,
    categorize: Callable[[str], tuple[str, str] | None] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Convert a raw CSV DataFrame into clean transaction rows.

    ``mapping`` maps logical field name -> CSV column name. ``account`` and
    ``currency`` entries may be ``None`` to fall back to the supplied defaults.
    ``categorize`` is an optional callable ``description -> category`` used to
    auto-apply rules at import time.

    Returns a tuple ``(valid_rows, skipped_rows)`` where skipped rows carry a
    ``_reason`` describing why they could not be parsed.
    """
    valid: list[dict] = []
    skipped: list[dict] = []

    for _, raw in df.iterrows():
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

    return valid, skipped
