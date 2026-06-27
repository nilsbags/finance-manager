"""Streamlit entry point — the Dashboard is the app's default landing page.

Run from the project root with:

    streamlit run app/Dashboard.py

Streamlit discovers the sibling ``pages/`` directory for the rest of the nav.

Leads with big "this month" KPI cards (spendings, earnings, net, savings rate)
each compared to last month, followed by a month-over-month comparison chart,
the spendings-vs-earnings trend, and category splits.
"""

import datetime as dt

import pandas as pd
import streamlit as st

import charts
import database
import money

st.set_page_config(page_title="Dashboard · Finance Manager", page_icon="📊", layout="wide")
database.init_db()

# A little styling to make the metric cards read as big, clean numbers.
st.markdown(
    """
    <style>
      [data-testid="stMetricValue"] { font-size: 2.3rem; font-weight: 700; }
      [data-testid="stMetricLabel"] p { font-size: 0.9rem; opacity: 0.75; }
      [data-testid="stMetricDelta"] { font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Dashboard")

# --- Current balance (one total, shown in each currency) ------------------- #
# Rendered first so it sits above everything else on the dashboard. It reads the
# stored running balances and is independent of the page's currency picker.
balances = database.get_account_balances()
if balances:
    rates = money.get_rates()
    st.subheader("💰 Current balance")
    bases = money.COMBINED_BASES  # EUR, USD, AED — same total, different currency
    balance_cols = st.columns(len(bases))
    for col, base in zip(balance_cols, bases):
        total = sum(money.convert_amount(b["balance"], b["currency"], base, rates) for b in balances)
        with col, st.container(border=True):
            st.metric(base, f"{total:,.0f} {base}")

df_all = database.fetch_transactions()
if df_all.empty:
    st.info("No transactions yet. Import a CSV on the **Import** page first.")
    st.stop()

# --- Currency (picked once for the whole page) ----------------------------- #
options = money.currency_options(df_all)
head_l, head_r = st.columns([3, 1])
with head_r:
    if len(options) > 1:
        selection = st.selectbox("Currency", options, key="dash_currency")
    else:
        selection = options[0]
    money.rates_editor(df_all, key="dash_fx")

# Resolve selection into a working frame (amounts in the display currency).
cur_df, currency = money.currency_view(df_all, selection)

# --- This-month vs last-month figures -------------------------------------- #
monthly = charts.monthly_totals(cur_df)
this_period = pd.Period(dt.date.today(), freq="M")
last_period = this_period - 1
has_prev = last_period in monthly.index


def _val(period: pd.Period, column: str) -> float:
    return float(monthly.loc[period, column]) if period in monthly.index else 0.0


spend_now, spend_prev = _val(this_period, "spend"), _val(last_period, "spend")
earn_now, earn_prev = _val(this_period, "income"), _val(last_period, "income")
net_now, net_prev = earn_now - spend_now, earn_prev - spend_prev
sr_now = (net_now / earn_now * 100) if earn_now > 0 else None
sr_prev = (net_prev / earn_prev * 100) if earn_prev > 0 else None

with head_l:
    st.subheader(f"{this_period.strftime('%B %Y')} · overview")
    st.caption("Big numbers are this month; deltas compare with last month.")


def _money_delta(now: float, prev: float) -> str | None:
    """Signed currency delta vs. last month, or None when there's no prior month."""
    if not has_prev:
        return None
    return f"{now - prev:+,.0f} {currency}"


# Big KPI cards.
k1, k2, k3, k4 = st.columns(4)
with k1:
    with st.container(border=True):
        st.metric(
            "Spendings",
            f"{spend_now:,.0f} {currency}",
            delta=_money_delta(spend_now, spend_prev),
            delta_color="inverse",  # spending more is "bad"
        )
with k2:
    with st.container(border=True):
        st.metric(
            "Earnings",
            f"{earn_now:,.0f} {currency}",
            delta=_money_delta(earn_now, earn_prev),
        )
with k3:
    with st.container(border=True):
        st.metric(
            "Net",
            f"{net_now:,.0f} {currency}",
            delta=_money_delta(net_now, net_prev),
        )
with k4:
    with st.container(border=True):
        sr_delta = (
            f"{sr_now - sr_prev:+.0f} pp"
            if (has_prev and sr_now is not None and sr_prev is not None)
            else None
        )
        st.metric(
            "Savings rate",
            f"{sr_now:.0f}%" if sr_now is not None else "—",
            delta=sr_delta,
        )

# --- Month-over-month comparison ------------------------------------------- #
st.subheader("Spendings vs. earnings by month")
if len(monthly) <= 1:
    st.caption("Not enough months of data yet to compare.")
else:
    st.plotly_chart(
        charts.monthly_comparison_chart(monthly, currency),
        width="stretch",
        key="dash_monthly",
    )

# --- Trend (period switcher + gradient chart) ------------------------------ #
st.subheader("Trend")
df, _, period = charts.overview_section(df_all, key_prefix="dash", show="both", currency=selection)

expenses = df[df["amount"] < 0].copy()
expenses["spend"] = expenses["amount"].abs()
income = df[df["amount"] > 0].copy()

# --- Category splits side by side (sunburst: category -> subcategory) ------ #
left, right = st.columns(2)

with left:
    st.subheader("Spending by category")
    if expenses.empty:
        st.caption("No spending in this period.")
    else:
        breakdown = charts.category_breakdown(expenses, "spend")
        st.plotly_chart(
            charts.hierarchy_chart(breakdown, "spend", currency, kind="sunburst"),
            width="stretch",
            key="dash_spend_sunburst",
        )

with right:
    st.subheader("Earnings by category")
    if income.empty:
        st.caption("No earnings in this period.")
    else:
        breakdown = charts.category_breakdown(income, "amount")
        st.plotly_chart(
            charts.hierarchy_chart(breakdown, "amount", currency, kind="sunburst"),
            width="stretch",
            key="dash_earn_sunburst",
        )
