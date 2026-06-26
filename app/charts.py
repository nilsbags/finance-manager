"""Shared analytics helpers for the Dashboard / Spendings / Earnings pages.

The centre-piece is :func:`overview_section`, which renders the period switcher
(This month / 3M / 6M / 1Y / YTD), optional account & currency filters, and the
gradient area chart of spendings vs. earnings. It returns the period-filtered
DataFrame so each page can build its own breakdowns below the shared chart.
"""

import calendar
import datetime as dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import categories
import money

# Colour palette shared across pages (RGB tuples reused for line + gradient).
SPEND_RGB = "239, 68, 68"   # red
EARN_RGB = "34, 197, 94"    # green

# Period options shown in the switcher; "This month" is the default.
PERIODS = ["This month", "3M", "6M", "1Y", "YTD"]

# Label used for transactions whose subcategory is blank, so hierarchy charts
# and the drill-down always have a leaf to show.
UNSPECIFIED = "(unspecified)"


def _add_months(d: dt.date, months: int) -> dt.date:
    """Return ``d`` shifted by ``months`` (negative shifts into the past)."""
    index = d.month - 1 + months
    year = d.year + index // 12
    month = index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def period_range(label: str, today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    """Translate a period label into a concrete ``(start, end)`` date range."""
    today = today or dt.date.today()
    match label:
        case "This month":
            start = today.replace(day=1)
        case "3M":
            start = _add_months(today, -3)
        case "6M":
            start = _add_months(today, -6)
        case "1Y":
            start = _add_months(today, -12)
        case "YTD":
            start = dt.date(today.year, 1, 1)
        case _:
            start = today.replace(day=1)
    return start, today


def choose_freq(start: dt.date, end: dt.date) -> str:
    """Pick a sensible resampling frequency for the span of the range.

    Tuned for a dense chart — each tier is one step finer than a plain
    daily/weekly/monthly split, giving roughly double the data points while
    staying readable: daily up to ~6 months, weekly up to ~3 years, then monthly.
    """
    days = (end - start).days
    if days <= 200:
        return "D"        # daily
    if days <= 1100:
        return "W"        # weekly
    return "MS"           # month start


def aggregate_timeseries(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Resample transactions into per-bucket ``spend`` and ``income`` totals.

    ``spend`` is returned as a positive number (the absolute value of expenses).
    Empty buckets within the data range are filled with zero so the area chart
    renders as a continuous gradient.
    """
    if df.empty:
        return pd.DataFrame(columns=["spend", "income"])

    series = df.set_index("date")["amount"].sort_index()
    spend = (-series[series < 0]).resample(freq).sum()
    income = series[series > 0].resample(freq).sum()
    out = pd.DataFrame({"spend": spend, "income": income}).fillna(0.0)
    return out.sort_index()


def _area_trace(x, y, name: str, rgb: str, currency: str) -> go.Scatter:
    """A line + subtle vertical (y-axis) gradient area trace."""
    return go.Scatter(
        x=x,
        y=y,
        name=name,
        mode="lines",
        line=dict(color=f"rgb({rgb})", width=2),
        fill="tozeroy",
        # Subtle gradient along the y-axis: fades from a light tint near the
        # line down to fully transparent at the baseline.
        fillgradient=dict(
            type="vertical",
            colorscale=[
                [0.0, f"rgba({rgb}, 0.00)"],
                [0.6, f"rgba({rgb}, 0.08)"],
                [1.0, f"rgba({rgb}, 0.22)"],
            ],
        ),
        hovertemplate=f"{name}: %{{y:,.2f}} {currency}<extra></extra>",
    )


def gradient_chart(ts: pd.DataFrame, currency: str, show: str = "both") -> go.Figure:
    """Build a gradient-filled area chart over time.

    ``show`` selects which series to draw: ``"both"`` (default), ``"spend"``
    (spendings only) or ``"earn"`` (earnings only).
    """
    fig = go.Figure()

    if show in ("both", "earn"):
        fig.add_trace(_area_trace(ts.index, ts["income"], "Earnings", EARN_RGB, currency))
    if show in ("both", "spend"):
        fig.add_trace(_area_trace(ts.index, ts["spend"], "Spendings", SPEND_RGB, currency))

    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        yaxis=dict(title=f"Amount ({currency})", rangemode="tozero"),
        xaxis=dict(title=None),
    )
    return fig


def category_breakdown(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Aggregate ``value_col`` by category + subcategory for hierarchy charts.

    Empty subcategories are labelled "(unspecified)" so every row has a leaf,
    which keeps sunburst/treemap rendering happy.
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "subcategory", value_col])
    d = df.copy()
    d["subcategory"] = d["subcategory"].replace("", pd.NA).fillna(UNSPECIFIED)
    return (
        d.groupby(["category", "subcategory"], as_index=False)[value_col]
        .sum()
        .sort_values(value_col, ascending=False)
    )


def hierarchy_chart(
    breakdown: pd.DataFrame, value_col: str, currency: str, kind: str = "sunburst"
) -> go.Figure:
    """Sunburst (default) or treemap of category -> subcategory totals.

    Sectors are coloured by their top-level category using the shared palette.
    """
    maker = px.sunburst if kind == "sunburst" else px.treemap
    fig = maker(
        breakdown,
        path=["category", "subcategory"],
        values=value_col,
        color="category",
        color_discrete_map={**categories.CATEGORY_COLORS, "(?)": "#cccccc"},
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>%{value:,.2f} " + currency + "<extra></extra>"
    )
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
    return fig


def monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Per-month ``spend`` (positive) and ``income`` totals, indexed by month.

    The caller is expected to pass a single-currency slice. The index is a
    pandas ``PeriodIndex`` (monthly), sorted ascending.
    """
    if df.empty:
        return pd.DataFrame(columns=["spend", "income"])
    d = df.copy()
    d["period"] = d["date"].dt.to_period("M")
    d["spend"] = (-d["amount"]).clip(lower=0)   # magnitude of expenses
    d["income"] = d["amount"].clip(lower=0)     # positive amounts only
    return d.groupby("period")[["spend", "income"]].sum().sort_index()


def monthly_comparison_chart(by_month: pd.DataFrame, currency: str, months: int = 12) -> go.Figure:
    """Grouped bar chart comparing spendings vs. earnings across recent months."""
    recent = by_month.tail(months)
    labels = recent.index.strftime("%b %Y")
    fig = go.Figure()
    fig.add_bar(x=labels, y=recent["spend"], name="Spendings", marker_color=f"rgb({SPEND_RGB})")
    fig.add_bar(x=labels, y=recent["income"], name="Earnings", marker_color=f"rgb({EARN_RGB})")
    fig.update_layout(
        barmode="group",
        height=340,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        yaxis=dict(title=f"Amount ({currency})", rangemode="tozero"),
        bargap=0.25,
    )
    fig.update_xaxes(type="category")
    return fig


def totals_bar(spent: float, earned: float, currency: str) -> go.Figure:
    """A simple two-bar comparison of total spendings vs. total earnings."""
    fig = go.Figure(
        go.Bar(
            x=["Spendings", "Earnings"],
            y=[spent, earned],
            marker_color=[f"rgb({SPEND_RGB})", f"rgb({EARN_RGB})"],
            text=[f"{spent:,.2f}", f"{earned:,.2f}"],
            textposition="outside",
            hovertemplate="%{x}: %{y:,.2f} " + currency + "<extra></extra>",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(title=f"Amount ({currency})", rangemode="tozero"),
        showlegend=False,
    )
    return fig


def overview_section(
    df_all: pd.DataFrame,
    key_prefix: str,
    show: str = "both",
    currency: str | None = None,
    cumulative: bool = False,
) -> tuple[pd.DataFrame, str, str]:
    """Render the shared controls + gradient chart at the top of a page.

    ``show`` controls which series the chart draws: ``"both"`` (Dashboard),
    ``"spend"`` (Spendings) or ``"earn"`` (Earnings). When ``currency`` is given,
    the currency picker is hidden and that currency is used (the Dashboard picks
    it once at the top of the page). When ``cumulative`` is True the series is
    accumulated over the period, so the line shows the running total evolving.

    Returns ``(df_period, currency, period_label)`` where ``df_period`` is the
    full transaction set filtered to the selected period, account(s) and
    currency — ready for each page to build its own breakdowns.
    """
    accounts = sorted(df_all["account"].unique())
    options = money.currency_options(df_all)

    # ``currency`` may be passed in as a selection (e.g. the Dashboard picks it
    # once for the whole page, along with its own rates editor). Otherwise we
    # render the currency picker — and the rates editor — here.
    selection = currency
    render_own_currency = currency is None
    if render_own_currency:
        c1, c2, c3 = st.columns([3, 1.4, 1])
        with c3:
            if len(options) > 1:
                selection = st.selectbox("Currency", options, key=f"{key_prefix}_currency")
            else:
                selection = options[0]
                st.metric("Currency", selection)
    else:
        c1, c2 = st.columns([3, 1.4])

    with c1:
        period = st.radio(
            "Period", PERIODS, horizontal=True, key=f"{key_prefix}_period"
        )
    with c2:
        sel_accounts = st.multiselect(
            "Account", accounts, key=f"{key_prefix}_accounts"
        )

    # Resolve the selection into a working frame (amounts in the display currency).
    work, currency = money.currency_view(df_all, selection)
    if render_own_currency:
        money.rates_editor(df_all, key=f"{key_prefix}_fx")

    start, end = period_range(period)

    mask = (work["date"].dt.date >= start) & (work["date"].dt.date <= end)
    if sel_accounts:
        mask &= work["account"].isin(sel_accounts)
    df_period = work[mask].copy()

    ts = aggregate_timeseries(df_period, choose_freq(start, end))

    title = {"spend": "Spendings", "earn": "Earnings"}.get(show, "Spendings vs. earnings")
    if cumulative:
        title = f"Cumulative {title.lower()}"
    combined_note = (
        f" · converted to {money.base_of(selection)}"
        if money.is_combined(selection)
        else ""
    )
    st.caption(f"{title} · {period} ({start:%d %b %Y} – {end:%d %b %Y}){combined_note}")

    # Decide whether there is anything to plot for the requested series (based on
    # the raw per-bucket totals, before any cumulative transform).
    if ts.empty:
        relevant_total = 0.0
    elif show == "spend":
        relevant_total = ts["spend"].sum()
    elif show == "earn":
        relevant_total = ts["income"].sum()
    else:
        relevant_total = ts["spend"].sum() + ts["income"].sum()

    # Accumulate over time so the chart shows the running total evolving.
    plot_ts = ts.cumsum() if (cumulative and not ts.empty) else ts

    if relevant_total == 0:
        st.info("No transactions in the selected period.")
    else:
        st.plotly_chart(
            gradient_chart(plot_ts, currency, show=show),
            width="stretch",
            key=f"{key_prefix}_gradient",
        )

    return df_period, currency, period
