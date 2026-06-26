"""Page: import a bank CSV, map its columns, and store transactions."""

import re

import pandas as pd
import streamlit as st

import database
import importer
import rules

st.set_page_config(page_title="Import · Finance Manager", page_icon="📥", layout="wide")
database.init_db()

st.title("📥 Import transactions")
st.caption("Upload a bank CSV, tell the app what each column means, and import.")

# --- Danger zone: reset stored transactions -------------------------------- #
existing_count = database.count_transactions()
with st.expander(f"⚠️ Danger zone — {existing_count} transaction(s) stored", expanded=False):
    st.caption(
        "Use this if an earlier import mapped the wrong columns. It removes all "
        "stored transactions (your category rules are kept) so you can re-import cleanly."
    )
    confirm = st.checkbox("Yes, delete all stored transactions", key="confirm_clear")
    if st.button("Clear all transactions", disabled=not confirm):
        removed = database.delete_all_transactions()
        st.success(f"Removed {removed} transaction(s). You can re-import below.")
        st.rerun()

uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV file to begin. Nothing is sent anywhere — parsing happens locally.")
    st.stop()

# --- Parsing options ------------------------------------------------------- #
with st.expander("Parsing options", expanded=False):
    c1, c2 = st.columns(2)
    delimiter = c1.selectbox(
        "Column delimiter", options=[",", ";", "\\t", "|"], index=0,
        help="Many European banks export with ';'.",
    )
    encoding = c2.selectbox("File encoding", options=["utf-8", "latin-1", "cp1252"], index=0)

real_delimiter = "\t" if delimiter == "\\t" else delimiter

try:
    df = pd.read_csv(uploaded, sep=real_delimiter, encoding=encoding, dtype=str)
except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
    st.error(f"Could not read the CSV: {exc}")
    st.stop()

if df.empty:
    st.warning("The uploaded file has no rows.")
    st.stop()

st.subheader("Preview")
st.dataframe(df.head(10), width="stretch")

# --- Column mapping -------------------------------------------------------- #
st.subheader("Map columns")
columns = list(df.columns)
none_label = "— not in file —"


def _guess(aliases: list[str]) -> int:
    """Best-matching column index for a field, given ranked name ``aliases``.

    Scoring prefers an exact name match, then "starts with", then "contains",
    so e.g. a real ``Description`` column beats ``Account name`` for the
    description field (a plain substring search would wrongly pick the latter).
    Returns 0 when nothing matches at all.
    """
    best_i, best_score = 0, 0
    for i, col in enumerate(columns):
        name = col.lower().strip()
        score = 0
        for rank, alias in enumerate(aliases):
            penalty = rank  # earlier aliases are stronger signals
            if name == alias:
                score = max(score, 100 - penalty)
            elif name.startswith(alias):
                score = max(score, 60 - penalty)
            elif alias in name:
                score = max(score, 30 - penalty)
        if score > best_score:
            best_i, best_score = i, score
    return best_i


def _guess_optional(aliases: list[str]) -> int:
    """Like ``_guess`` but returns an index into ``[none_label] + columns``.

    Falls back to 0 (── not in file ──) when no column is a clear match.
    """
    best_i, best_score = 0, 0
    for i, col in enumerate(columns):
        name = col.lower().strip()
        for rank, alias in enumerate(aliases):
            if name == alias:
                score = 100 - rank
            elif name.startswith(alias):
                score = 60 - rank
            elif alias in name:
                score = 30 - rank
            else:
                continue
            if score > best_score:
                best_i, best_score = i + 1, score  # +1 to skip none_label
    return best_i


def _sample(series: pd.Series, limit: int = 300) -> list[str]:
    """First ``limit`` non-empty string values of a column."""
    out: list[str] = []
    for v in series.dropna():
        s = str(v).strip()
        if s and s.lower() != "nan":
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _detect_dayfirst(series: pd.Series, fallback: bool = True) -> bool:
    """Guess whether the date column is day-first, adapting to the file.

    ISO ``YYYY-MM-DD`` dates are not day-first. For ``D/M/Y`` vs ``M/D/Y`` we
    disambiguate using any component > 12 (a 13+ in the first slot means
    day-first; in the second slot means month-first). Falls back to the
    European convention (day-first) when it's genuinely ambiguous.
    """
    vals = _sample(series)
    if not vals:
        return fallback
    iso = sum(bool(re.match(r"^\d{4}-\d{1,2}-\d{1,2}", v)) for v in vals)
    if iso / len(vals) >= 0.6:
        return False
    first_gt12 = second_gt12 = 0
    for v in vals:
        m = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-]\d{2,4}", v)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            first_gt12 += a > 12
            second_gt12 += b > 12
    if first_gt12 > second_gt12:
        return True
    if second_gt12 > first_gt12:
        return False
    return fallback


def _detect_decimal_comma(series: pd.Series) -> bool:
    """Guess whether amounts use a comma decimal separator (e.g. 1.234,56)."""
    vals = _sample(series)
    comma = total = 0
    for v in vals:
        last_dot, last_comma = v.rfind("."), v.rfind(",")
        if last_dot == -1 and last_comma == -1:
            continue
        total += 1
        comma += last_comma > last_dot
    return total > 0 and comma / total >= 0.5


c1, c2, c3 = st.columns(3)
date_col = c1.selectbox(
    "Date column", columns,
    index=_guess(["date", "buchungsdatum", "datum", "booking date", "value date", "booking"]),
)
desc_col = c2.selectbox(
    "Description column", columns,
    index=_guess(
        ["description", "desc", "payee", "merchant", "narrative",
         "verwendungszweck", "verwendung", "details", "text"]
    ),
)
amount_col = c3.selectbox(
    "Amount column", columns,
    index=_guess(["amount", "betrag", "umsatz", "value", "sum"]),
)

c4, c5, c10 = st.columns(3)
account_choice = c4.selectbox(
    "Account column (optional)", [none_label] + columns,
    index=_guess_optional(["account name", "account", "konto", "card number", "card", "iban"]),
)
currency_choice = c5.selectbox(
    "Currency column (optional)", [none_label] + columns,
    index=_guess_optional(["currency", "account currency", "währung", "waehrung", "ccy"]),
)
balance_choice = c10.selectbox(
    "Balance column (optional)", [none_label] + columns,
    index=_guess_optional(
        ["balance", "running balance", "saldo", "kontostand", "saldo nach buchung", "new balance"]
    ),
    help="The running account balance. Lets the app recover income that only "
    "shows up as a balance jump, not as its own transaction.",
)

c6, c7 = st.columns(2)
default_account = c6.text_input(
    "Default account", value="Main",
    help="Used when no account column is selected.",
)
default_currency = c7.text_input("Default currency", value="EUR")

# Defaults auto-detected from the uploaded file's date / amount columns.
comma_default = _detect_decimal_comma(df[amount_col])
dayfirst_default = _detect_dayfirst(df[date_col])

c8, c9 = st.columns(2)
decimal_comma = c8.checkbox(
    "Amounts use comma as decimal (e.g. 1.234,56)", value=comma_default,
    help="Auto-detected from your amount column — override if needed.",
)
dayfirst = c9.checkbox(
    "Dates are day-first (e.g. 31/12/2025)", value=dayfirst_default,
    help="Auto-detected from your date column (ISO dates are not day-first).",
)

apply_rules_on_import = st.checkbox(
    "Auto-categorize using rules during import", value=True
)

has_balance = balance_choice != none_label
deduce_income = st.checkbox(
    "Deduce income/changes from balance gaps",
    value=has_balance,
    disabled=not has_balance,
    help="When the running balance moves by more than the listed transactions in "
    "a month, the difference is added as a synthetic entry per account and month — "
    "positive months as income, negative months as an outflow. Needs a balance column.",
)

# --- Import ---------------------------------------------------------------- #
if st.button("Import transactions", type="primary"):
    mapping = {
        "date": date_col,
        "description": desc_col,
        "amount": amount_col,
        "account": None if account_choice == none_label else account_choice,
        "currency": None if currency_choice == none_label else currency_choice,
        "balance": None if balance_choice == none_label else balance_choice,
    }

    categorize_fn = None
    if apply_rules_on_import:
        loaded_rules = rules.load_rules()
        categorize_fn = lambda desc: rules.categorize(desc, loaded_rules)  # noqa: E731

    valid, skipped = importer.prepare_rows(
        df,
        mapping,
        default_account=default_account,
        default_currency=default_currency,
        decimal_comma=decimal_comma,
        dayfirst=dayfirst,
        categorize=categorize_fn,
        deduce_income=deduce_income,
    )

    deduced = sum(
        r["description"] in (importer.DEDUCED_INCOME_DESC, importer.DEDUCED_OUTFLOW_DESC)
        for r in valid
    )
    inserted = database.insert_transactions(valid)
    duplicates = len(valid) - inserted

    # Persist the latest running balance per account so the dashboard can show it.
    balances = []
    if mapping["balance"]:
        balances = importer.latest_balances(
            df,
            mapping,
            default_account=default_account,
            default_currency=default_currency,
            decimal_comma=decimal_comma,
            dayfirst=dayfirst,
        )
        if balances:
            database.update_account_balances(balances)

    msg = (
        f"Imported {inserted} new transaction(s). "
        f"Skipped {duplicates} duplicate(s) and {len(skipped)} unparseable row(s)."
    )
    if deduced:
        msg += f" Includes {deduced} entr(y/ies) deduced from balance changes."
    if balances:
        msg += f" Updated current balance for {len(balances)} account(s)."
    st.success(msg)

    if skipped:
        with st.expander(f"Show {len(skipped)} skipped row(s)"):
            st.dataframe(pd.DataFrame(skipped), width="stretch")
