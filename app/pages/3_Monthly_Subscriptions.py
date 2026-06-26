"""Page: detect and list recurring monthly subscriptions to spot savings."""

import plotly.express as px
import streamlit as st

import categories
import database
import money
import subscriptions

st.set_page_config(
    page_title="Subscriptions · Finance Manager", page_icon="🔁", layout="wide"
)
database.init_db()

st.title("🔁 Monthly subscriptions")
st.caption(
    "Recurring charges detected from your transactions — review them and cancel "
    "what you no longer use to save money."
)

df_all = database.fetch_transactions()
if df_all.empty:
    st.info("No transactions yet. Import a CSV on the **Import** page first.")
    st.stop()

# --- Detection settings ---------------------------------------------------- #
with st.expander("Detection settings"):
    c1, c2, c3 = st.columns(3)
    min_occ = c1.slider("Minimum charges", 2, 6, subscriptions.DEFAULT_MIN_OCCURRENCES)
    max_cv = c2.slider(
        "Max amount variation", 0.0, 1.0, subscriptions.DEFAULT_MAX_AMOUNT_CV, 0.05,
        help="Lower = stricter (amounts must be more consistent).",
    )
    include_cat = c3.checkbox(
        "Include subscription-type categories & names", value=True,
        help="Count merchants in Software & Subscriptions, Streaming, Phone & "
        "Internet — or whose name contains 'subscription' (e.g. 'Claude "
        "Subscription') — even when the cadence is irregular, as long as it "
        "stays monthly or longer (weekly/shorter charges are never counted).",
    )
    st.caption("Conversion rates below are used for the combined EUR totals.")
    money.rates_editor(df_all, key="subs_fx")

f1, f2 = st.columns(2)
high_only = f1.toggle("Likely subscriptions only (High confidence)", value=True)
show_inactive = f2.toggle("Show inactive", value=True)

# --- Detect ---------------------------------------------------------------- #
subs = subscriptions.detect(
    df_all, min_occurrences=min_occ, max_amount_cv=max_cv,
    include_category_matches=include_cat,
)

if high_only and not subs.empty:
    subs = subs[subs["confidence"] == "High"]
if not show_inactive and not subs.empty:
    subs = subs[subs["active"]]

if subs.empty:
    st.info(
        "No recurring monthly charges detected with the current settings. "
        "Try lowering the minimum charges or raising the amount-variation limit."
    )
    st.stop()

# Convert each subscription's typical amount to EUR for comparable totals.
rates = money.get_rates()
subs = subs.copy()
subs["monthly_eur"] = subs.apply(
    lambda r: r["typical_amount"] * rates.get(r["currency"], 1.0), axis=1
)
subs["annual_eur"] = subs["monthly_eur"] * 12
subs["category_label"] = subs.apply(
    lambda r: f"{r['category']} › {r['subcategory']}" if r["subcategory"] else r["category"],
    axis=1,
)
subs["price"] = subs.apply(lambda r: f"{r['typical_amount']:,.2f} {r['currency']}", axis=1)
subs["status"] = subs["active"].map({True: "🟢 Active", False: "⚪ Inactive"})

# --- Summary metrics ------------------------------------------------------- #
active = subs[subs["active"]]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Subscriptions", f"{len(subs)}")
m2.metric("Active", f"{len(active)}")
m3.metric("Monthly (active)", f"€{active['monthly_eur'].sum():,.0f}")
m4.metric("Per year (active)", f"€{active['annual_eur'].sum():,.0f}")

st.caption(
    "Totals are converted to EUR using your manual rates. 'Active' means charged "
    "within the last ~45 days of your data."
)

# --- Savings chart: biggest subscriptions by yearly cost ------------------- #
st.subheader("Where your subscription money goes (per year)")
chart_df = subs.sort_values("annual_eur").tail(15)
fig = px.bar(
    chart_df, x="annual_eur", y="merchant", orientation="h", color="category",
    labels={"annual_eur": "Per year (€)", "merchant": ""},
    color_discrete_map=categories.CATEGORY_COLORS,
)
fig.update_layout(
    height=max(280, 34 * len(chart_df)), showlegend=False,
    margin=dict(l=10, r=10, t=10, b=10), yaxis={"categoryorder": "total ascending"},
)
fig.update_traces(hovertemplate="%{y}: €%{x:,.0f}/yr<extra></extra>")
st.plotly_chart(fig, width="stretch")

# --- Detailed list --------------------------------------------------------- #
st.subheader("All detected subscriptions")
st.dataframe(
    subs[[
        "merchant", "category_label", "price", "monthly_eur", "annual_eur",
        "occurrences", "median_gap_days", "last_seen", "status", "confidence",
    ]],
    width="stretch",
    hide_index=True,
    column_config={
        "merchant": "Merchant",
        "category_label": "Category",
        "price": "Typical charge",
        "monthly_eur": st.column_config.NumberColumn("Monthly (€)", format="€%.2f"),
        "annual_eur": st.column_config.NumberColumn("Per year (€)", format="€%.0f"),
        "occurrences": st.column_config.NumberColumn("Charges", width="small"),
        "median_gap_days": st.column_config.NumberColumn("Every ~days", width="small"),
        "last_seen": st.column_config.DateColumn("Last charge"),
        "status": "Status",
        "confidence": "Confidence",
    },
)

# --- A nudge toward savings ------------------------------------------------ #
if not active.empty:
    top = active.sort_values("annual_eur", ascending=False).iloc[0]
    st.info(
        f"💡 Your most expensive active subscription is **{top['merchant']}** at "
        f"about **€{top['annual_eur']:,.0f}/year**. Cancelling the subscriptions "
        f"you don't use could save up to **€{active['annual_eur'].sum():,.0f}/year**."
    )
