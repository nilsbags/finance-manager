"""Page: import a bank CSV, map its columns, and store transactions."""

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

c4, c5 = st.columns(2)
account_choice = c4.selectbox(
    "Account column (optional)", [none_label] + columns,
    index=_guess_optional(["account name", "account", "konto", "card number", "card", "iban"]),
)
currency_choice = c5.selectbox(
    "Currency column (optional)", [none_label] + columns,
    index=_guess_optional(["currency", "account currency", "währung", "waehrung", "ccy"]),
)

c6, c7 = st.columns(2)
default_account = c6.text_input(
    "Default account", value="Main",
    help="Used when no account column is selected.",
)
default_currency = c7.text_input("Default currency", value="EUR")

c8, c9 = st.columns(2)
decimal_comma = c8.checkbox(
    "Amounts use comma as decimal (e.g. 1.234,56)", value=False
)
dayfirst = c9.checkbox("Dates are day-first (e.g. 31/12/2025)", value=True)

apply_rules_on_import = st.checkbox(
    "Auto-categorize using rules during import", value=True
)

# --- Import ---------------------------------------------------------------- #
if st.button("Import transactions", type="primary"):
    mapping = {
        "date": date_col,
        "description": desc_col,
        "amount": amount_col,
        "account": None if account_choice == none_label else account_choice,
        "currency": None if currency_choice == none_label else currency_choice,
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
    )

    inserted = database.insert_transactions(valid)
    duplicates = len(valid) - inserted

    st.success(
        f"Imported {inserted} new transaction(s). "
        f"Skipped {duplicates} duplicate(s) and {len(skipped)} unparseable row(s)."
    )

    if skipped:
        with st.expander(f"Show {len(skipped)} skipped row(s)"):
            st.dataframe(pd.DataFrame(skipped), width="stretch")
