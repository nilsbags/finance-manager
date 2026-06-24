"""Page: earnings-focused breakdowns under the shared gradient chart."""

import plotly.express as px
import streamlit as st

import categories
import charts
import database

st.set_page_config(page_title="Earnings · Finance Manager", page_icon="💰", layout="wide")
database.init_db()

st.title("💰 Earnings")

df_all = database.fetch_transactions()
if df_all.empty:
    st.info("No transactions yet. Import a CSV on the **Import** page first.")
    st.stop()

# Period switcher + cumulative gradient chart showing how earnings add up over time.
df, currency, period = charts.overview_section(
    df_all, key_prefix="earn", show="earn", cumulative=True
)

income = df[df["amount"] > 0].copy()
if income.empty:
    st.info("No earnings in the selected period.")
    st.stop()
income["month"] = income["date"].dt.to_period("M")

# --- Metrics --------------------------------------------------------------- #
m1, m2, m3 = st.columns(3)
m1.metric(f"Total earned ({currency})", f"{income['amount'].sum():,.2f}")
m2.metric("Transactions", f"{len(income):,}")
m3.metric(f"Avg / transaction ({currency})", f"{income['amount'].mean():,.2f}")

# --- By category & subcategory (treemap) ----------------------------------- #
st.subheader("Earnings by category & subcategory")
breakdown = charts.category_breakdown(income, "amount")
st.plotly_chart(
    charts.hierarchy_chart(breakdown, "amount", currency, kind="treemap"),
    width="stretch",
    key="earn_treemap",
)

# --- By subcategory (bar) -------------------------------------------------- #
st.subheader("Top subcategories")
by_sub = breakdown.copy()
by_sub["label"] = by_sub["category"] + " › " + by_sub["subcategory"]
by_sub = by_sub.sort_values("amount", ascending=False).head(15)
fig_sub = px.bar(by_sub, x="amount", y="label", orientation="h", color="category",
                 labels={"amount": f"Earned ({currency})", "label": ""},
                 color_discrete_map=categories.CATEGORY_COLORS)
fig_sub.update_layout(yaxis={"categoryorder": "total ascending"}, height=380,
                      margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
st.plotly_chart(fig_sub, width="stretch")

# --- By month -------------------------------------------------------------- #
st.subheader("Earnings by month")
by_month = income.groupby("month", as_index=False)["amount"].sum().sort_values("month")
by_month["label"] = by_month["month"].dt.strftime("%b %Y")
fig_month = px.bar(by_month, x="label", y="amount",
                   labels={"amount": f"Earned ({currency})", "label": ""},
                   color_discrete_sequence=[f"rgb({charts.EARN_RGB})"])
fig_month.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
# Treat months as discrete categories so the axis shows "Jan 2026", not dates.
fig_month.update_xaxes(type="category")
st.plotly_chart(fig_month, width="stretch")

# --- Top sources ----------------------------------------------------------- #
st.subheader("Top sources")
top = (income.groupby("description", as_index=False)["amount"].sum()
       .sort_values("amount", ascending=False).head(15))
st.dataframe(top, width="stretch", hide_index=True,
             column_config={"description": "Source",
                            "amount": st.column_config.NumberColumn(f"Earned ({currency})", format="%.2f")})
