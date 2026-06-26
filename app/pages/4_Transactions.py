"""Page: drill-down explorer (category → subcategory → transactions) + editor.

Click a category bar to expand it into its subcategories; click a subcategory
to narrow the editable transactions table below to exactly those rows. A
breadcrumb lets you step back up. Search / account filters apply throughout.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import categories
import charts
import database
import money
import rules

# Time-window switcher for this page. "All time" applies no date filter.
TX_PERIODS = ["1M", "3M", "1Y", "All time"]
_TX_PERIOD_MONTHS = {"1M": 1, "3M": 3, "1Y": 12}


def _period_start(label: str) -> str | None:
    """ISO start date for a period label, or ``None`` for the all-time view."""
    months = _TX_PERIOD_MONTHS.get(label)
    if months is None:
        return None
    start = (pd.Timestamp.today().normalize() - pd.DateOffset(months=months)).date()
    return start.isoformat()


st.set_page_config(
    page_title="Transactions · Finance Manager", page_icon="📂", layout="wide"
)
database.init_db()

st.title("📂 Transactions")

df_all = database.fetch_transactions()
if df_all.empty:
    st.info("No transactions yet. Import a CSV on the **Import** page first.")
    st.stop()

# --- Time window ----------------------------------------------------------- #
period = st.radio(
    "Period", TX_PERIODS, index=len(TX_PERIODS) - 1, horizontal=True, key="tx_period"
)
start_date = _period_start(period)

# --- Filters --------------------------------------------------------------- #
f1, f2, f3 = st.columns([2, 1, 1])
search = f1.text_input("Search description or notes", value="")
accounts = database.distinct_values("account")
sel_accounts = f2.multiselect("Account", accounts)
cur_options = money.currency_options(df_all)
sel_currency = f3.selectbox("Chart currency", cur_options, help="Sizes the drill-down bars.")
money.rates_editor(df_all, key="tx_fx")

# Drill-down state lives in the session so clicks survive reruns.
cat = st.session_state.get("tx_cat")
sub = st.session_state.get("tx_sub")


def _clear(level: str):
    """Step back up the breadcrumb (used as a button on_click callback).

    Also drops the relevant chart's stored selection so a remembered click does
    not immediately re-drill on the next render.
    """
    if level == "all":
        for k in ("tx_cat", "tx_sub", "tx_cat_chart", "tx_sub_chart"):
            st.session_state.pop(k, None)
    elif level == "cat":
        for k in ("tx_sub", "tx_sub_chart"):
            st.session_state.pop(k, None)


def _clicked_label(event) -> str | None:
    """Extract the clicked bar's category/subcategory label from a select event."""
    try:
        points = event["selection"]["points"]
    except (KeyError, TypeError):
        return None
    if not points:
        return None
    pt = points[0]
    # Horizontal bars carry the label on ``y``; fall back defensively.
    return pt.get("y") or pt.get("label") or pt.get("x")


# --- Breadcrumb ------------------------------------------------------------ #
b1, b2, b3 = st.columns([1.2, 1.6, 5])
b1.button("🏠 All categories", on_click=lambda: _clear("all"),
          disabled=cat is None, width="stretch")
if cat:
    b2.button(f"◂ {cat}", on_click=lambda: _clear("cat"),
              disabled=sub is None, help="Back to subcategories", width="stretch")
crumb = "All categories"
if cat:
    crumb += f"  ›  **{cat}**"
if sub:
    crumb += f"  ›  **{sub}**"
b3.markdown(f"<div style='padding-top:0.5rem'>{crumb}</div>", unsafe_allow_html=True)

# --- Base frame for the drill bars (period + search/account + currency) ---- #
base = database.fetch_transactions(
    search=search or None, accounts=sel_accounts or None, start_date=start_date
)
base, disp_currency = money.currency_view(base, sel_currency)
base["volume"] = base["amount"].abs()

# --- Drill-down charts ----------------------------------------------------- #
if base.empty:
    st.info("No transactions match your search/account filters.")
elif cat is None:
    st.caption("Click a **category** bar to drill in.")
    by_cat = base.groupby("category", as_index=False)["volume"].sum().sort_values("volume")
    fig = px.bar(by_cat, x="volume", y="category", orientation="h", color="category",
                 labels={"volume": f"Total ({disp_currency})", "category": ""},
                 color_discrete_map=categories.CATEGORY_COLORS)
    fig.update_layout(height=max(260, 36 * len(by_cat)), showlegend=False,
                      margin=dict(l=10, r=10, t=10, b=10),
                      yaxis={"categoryorder": "total ascending"})
    event = st.plotly_chart(fig, on_select="rerun", selection_mode="points",
                            key="tx_cat_chart", width="stretch")
    label = _clicked_label(event)
    if label:
        st.session_state["tx_cat"] = label
        st.session_state.pop("tx_sub", None)  # start fresh at the subcategory level
        st.rerun()
elif sub is None:
    st.caption(f"Click a **subcategory** of *{cat}* to see its transactions.")
    scoped = base[base["category"] == cat]
    bd = charts.category_breakdown(scoped, "volume").sort_values("volume")
    fig = px.bar(bd, x="volume", y="subcategory", orientation="h",
                 labels={"volume": f"Total ({disp_currency})", "subcategory": ""},
                 color_discrete_sequence=[categories.color_for(cat)])
    fig.update_layout(height=max(220, 40 * len(bd)), showlegend=False,
                      margin=dict(l=10, r=10, t=10, b=10),
                      yaxis={"categoryorder": "total ascending"})
    event = st.plotly_chart(fig, on_select="rerun", selection_mode="points",
                            key="tx_sub_chart", width="stretch")
    label = _clicked_label(event)
    if label:
        st.session_state["tx_sub"] = label
        st.rerun()

# --- Transactions table (narrowed to the current drill path) --------------- #
# Map the "(unspecified)" leaf back to the stored empty-string subcategory.
sub_filter = None
if sub:
    sub_filter = [""] if sub == charts.UNSPECIFIED else [sub]

df = database.fetch_transactions(
    search=search or None,
    accounts=sel_accounts or None,
    categories=[cat] if cat else None,
    subcategories=sub_filter,
    start_date=start_date,
)

st.divider()
st.subheader("Transactions")
period_note = "all time" if start_date is None else f"last {period}"
st.caption(
    f"Showing {len(df)} transaction(s) · {period_note}. Edit **category**, "
    "**subcategory** and **notes** inline, then save."
)

cat_options = sorted(set(categories.all_categories()) | set(database.distinct_values("category")))
sub_options = sorted(set(categories.all_subcategories()) | set(database.distinct_values("subcategory")))

edited = st.data_editor(
    df,
    width="stretch",
    height=620,
    hide_index=True,
    disabled=["id", "date", "description", "amount", "account", "currency"],
    column_config={
        "id": st.column_config.NumberColumn("ID", width="small"),
        "date": st.column_config.DateColumn("Date"),
        "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        "category": st.column_config.SelectboxColumn("Category", options=cat_options, required=True),
        "subcategory": st.column_config.SelectboxColumn("Subcategory", options=[""] + sub_options),
        "notes": st.column_config.TextColumn("Notes"),
    },
    key="tx_editor",
)

col_save, col_rules = st.columns(2)

if col_save.button("Save changes", type="primary"):
    original = df.set_index("id")
    changed = 0
    for _, row in edited.iterrows():
        tx_id = int(row["id"])
        before = original.loc[tx_id]
        new_cat = row["category"]
        new_sub = row["subcategory"] or ""
        valid_subs = categories.subcategories(new_cat)
        if new_sub and valid_subs and new_sub not in valid_subs:
            new_sub = ""
        new_notes = row["notes"] or ""
        if (
            new_cat != before["category"]
            or new_sub != (before["subcategory"] or "")
            or new_notes != (before["notes"] or "")
        ):
            database.update_transaction(tx_id, category=new_cat, subcategory=new_sub, notes=new_notes)
            changed += 1
    st.success(f"Saved {changed} change(s).")
    st.rerun()

if col_rules.button("Apply rules to uncategorized"):
    n = rules.apply_rules_to_existing(only_uncategorized=True)
    st.success(f"Updated {n} transaction(s) from category rules.")
    st.rerun()
