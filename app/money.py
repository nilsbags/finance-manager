"""Currency handling: a combined "All → EUR" view with manual FX rates.

The app is local-first with no external API, so exchange rates are entered by
hand and stored in the ``meta`` table. ``currency_view`` turns a currency
*selection* (a single code, or the combined ``ALL_EUR`` option) into a working
DataFrame whose ``amount`` is expressed in the display currency.
"""

import json

import pandas as pd
import streamlit as st

import database

# Sentinel label for the "convert everything into EUR" option.
ALL_EUR = "All → EUR"
BASE = "EUR"

# Sensible starting rates (1 unit of currency = N EUR). User-editable in the UI.
DEFAULT_RATES: dict[str, float] = {
    "EUR": 1.0,
    "USD": 0.92,
    "AED": 0.25,
    "GBP": 1.17,
    "CHF": 1.06,
}

_META_KEY = "fx_rates_to_eur"


def get_rates() -> dict[str, float]:
    """Return EUR conversion rates, merging any user overrides over defaults."""
    rates = dict(DEFAULT_RATES)
    raw = database.get_meta(_META_KEY)
    if raw:
        try:
            rates.update({k: float(v) for k, v in json.loads(raw).items()})
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    return rates


def set_rates(rates: dict[str, float]) -> None:
    """Persist user-edited conversion rates."""
    database.set_meta(_META_KEY, json.dumps(rates))


def currency_options(df_all: pd.DataFrame) -> list[str]:
    """Currency picker options: the combined view first (if >1 currency)."""
    curs = sorted(df_all["currency"].unique())
    return [ALL_EUR, *curs] if len(curs) > 1 else curs


def currency_view(
    df_all: pd.DataFrame, selection: str, rates: dict[str, float] | None = None
) -> tuple[pd.DataFrame, str]:
    """Return ``(working_df, display_currency)`` for a currency selection.

    For a single currency this is just a filtered copy. For ``ALL_EUR`` every
    row's amount is converted to EUR using ``rates`` and the currency column is
    normalised to EUR, so downstream aggregation simply works.
    """
    if rates is None:
        rates = get_rates()

    if selection == ALL_EUR:
        work = df_all.copy()
        factor = work["currency"].map(lambda c: rates.get(c, 1.0))
        work["amount"] = work["amount"] * factor
        work["currency"] = BASE
        return work, BASE

    return df_all[df_all["currency"] == selection].copy(), selection


def rates_editor(df_all: pd.DataFrame, key: str) -> None:
    """Render an expander to edit the manual EUR conversion rates.

    Only shown when the data spans more than one currency (otherwise there is
    nothing to convert).
    """
    others = [c for c in sorted(df_all["currency"].unique()) if c != BASE]
    if not others:
        return

    rates = get_rates()
    with st.expander("💱 Conversion rates (→ EUR)"):
        st.caption(
            "Used for the combined **All → EUR** view. No external API — set "
            "these manually to match your bank/statement period."
        )
        cols = st.columns(len(others))
        updated = dict(rates)
        for col, cur in zip(cols, others):
            updated[cur] = col.number_input(
                f"1 {cur} = ? EUR",
                value=float(rates.get(cur, DEFAULT_RATES.get(cur, 1.0))),
                min_value=0.0,
                step=0.01,
                format="%.4f",
                key=f"{key}_rate_{cur}",
            )
        if updated != rates:
            set_rates(updated)
