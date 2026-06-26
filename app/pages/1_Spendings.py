"""Page: spending-focused breakdowns under the shared gradient chart."""

import plotly.express as px
import streamlit as st

import categories
import charts
import database

st.set_page_config(page_title="Spendings · Finance Manager", page_icon="🛒", layout="wide")
database.init_db()

st.title("🛒 Spendings")

df_all = database.fetch_transactions()
if df_all.empty:
    st.info("No transactions yet. Import a CSV on the **Import** page first.")
    st.stop()

# Period switcher + cumulative gradient chart showing how spendings add up over time.
df, currency, period = charts.overview_section(
    df_all, key_prefix="spend", show="spend", cumulative=True
)

expenses = df[df["amount"] < 0].copy()
if expenses.empty:
    st.info("No spending in the selected period.")
    st.stop()
expenses["spend"] = expenses["amount"].abs()
expenses["month"] = expenses["date"].dt.to_period("M")

# --- Metrics --------------------------------------------------------------- #
m1, m2, m3 = st.columns(3)
m1.metric(f"Total spent ({currency})", f"{expenses['spend'].sum():,.2f}")
m2.metric("Transactions", f"{len(expenses):,}")
m3.metric(f"Avg / transaction ({currency})", f"{expenses['spend'].mean():,.2f}")

# --- By category & subcategory (treemap) ----------------------------------- #
st.subheader("Spending by category & subcategory")
breakdown = charts.category_breakdown(expenses, "spend")
st.plotly_chart(
    charts.hierarchy_chart(breakdown, "spend", currency, kind="treemap"),
    width="stretch",
    key="spend_treemap",
)

# --- By subcategory (bar) -------------------------------------------------- #
st.subheader("Top subcategories")
by_sub = breakdown.copy()
by_sub["label"] = by_sub["category"] + " › " + by_sub["subcategory"]
by_sub = by_sub.sort_values("spend", ascending=False).head(15)
fig_sub = px.bar(by_sub, x="spend", y="label", orientation="h", color="category",
                 labels={"spend": f"Spent ({currency})", "label": ""},
                 color_discrete_map=categories.CATEGORY_COLORS)
fig_sub.update_layout(yaxis={"categoryorder": "total ascending"}, height=380,
                      margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
st.plotly_chart(fig_sub, width="stretch")

# --- By month -------------------------------------------------------------- #
st.subheader("Spending by month")
by_month = expenses.groupby("month", as_index=False)["spend"].sum().sort_values("month")
by_month["label"] = by_month["month"].dt.strftime("%b %Y")
fig_month = px.bar(by_month, x="label", y="spend",
                   labels={"spend": f"Spent ({currency})", "label": ""},
                   color_discrete_sequence=[f"rgb({charts.SPEND_RGB})"])
fig_month.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
# Treat months as discrete categories so the axis shows "Jan 2026", not dates.
fig_month.update_xaxes(type="category")
st.plotly_chart(fig_month, width="stretch")

# --- Top merchants --------------------------------------------------------- #
st.subheader("Top merchants")
top = (expenses.groupby("description", as_index=False)["spend"].sum()
       .sort_values("spend", ascending=False).head(15))
st.dataframe(top, width="stretch", hide_index=True,
             column_config={"description": "Merchant",
                            "spend": st.column_config.NumberColumn(f"Spent ({currency})", format="%.2f")})
