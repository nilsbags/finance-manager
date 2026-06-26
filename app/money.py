"""Currency handling: combined "All → <currency>" views with manual FX rates.

The app is local-first with no external API, so exchange rates are entered by
hand and stored in the ``meta`` table. Rates are stored relative to a single
pivot (EUR); conversions into any other target base are derived from them.
``currency_view`` turns a currency *selection* (a single code, or one of the
combined ``All → …`` options) into a working DataFrame whose ``amount`` is
expressed in the display currency.
"""

import json

import pandas as pd
import streamlit as st

import database

# Pivot currency the stored rates are expressed against (1 unit = N EUR).
BASE = "EUR"

# Target bases offered as combined "All → …" views, in display order. EUR is
# first so it is the default selection in every currency picker.
COMBINED_BASES: tuple[str, ...] = ("EUR", "USD", "AED")


def combined_label(base: str) -> str:
    """Human label for a combined view into ``base`` (e.g. ``"All → USD"``)."""
    return f"All → {base}"


# Convenience constants + lookups.
ALL_EUR = combined_label("EUR")
ALL_USD = combined_label("USD")
ALL_AED = combined_label("AED")
COMBINED_LABELS: list[str] = [combined_label(b) for b in COMBINED_BASES]
_BASE_BY_LABEL: dict[str, str] = {combined_label(b): b for b in COMBINED_BASES}

# Sensible starting rates (1 unit of currency = N EUR). User-editable in the UI.
DEFAULT_RATES: dict[str, float] = {
    "EUR": 1.0,
    "USD": 0.92,
    "AED": 0.25,
    "GBP": 1.17,
    "CHF": 1.06,
}

_META_KEY = "fx_rates_to_eur"


def is_combined(selection: str) -> bool:
    """True if ``selection`` is one of the combined "All → …" options."""
    return selection in _BASE_BY_LABEL


def base_of(selection: str) -> str | None:
    """Target currency code for a combined selection, else ``None``."""
    return _BASE_BY_LABEL.get(selection)


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
    """Currency picker options.

    With more than one currency the combined "All → …" views come first (EUR
    leading, so it is the default), followed by each individual currency.
    """
    curs = sorted(df_all["currency"].unique())
    return [*COMBINED_LABELS, *curs] if len(curs) > 1 else curs


def _rate_to_eur(cur: str, rates: dict[str, float]) -> float:
    return rates.get(cur, DEFAULT_RATES.get(cur, 1.0))


def convert_amount(
    amount: float, from_cur: str, to_cur: str, rates: dict[str, float] | None = None
) -> float:
    """Convert a single amount between currencies via the EUR pivot rates."""
    if from_cur == to_cur:
        return amount
    if rates is None:
        rates = get_rates()
    return amount * (_rate_to_eur(from_cur, rates) / (_rate_to_eur(to_cur, rates) or 1.0))


def currency_view(
    df_all: pd.DataFrame, selection: str, rates: dict[str, float] | None = None
) -> tuple[pd.DataFrame, str]:
    """Return ``(working_df, display_currency)`` for a currency selection.

    For a single currency this is just a filtered copy. For a combined
    ``All → <base>`` view every row's amount is converted into ``base`` and the
    currency column is normalised, so downstream aggregation simply works.

    Conversion uses the EUR pivot: ``amount_base = amount * (rate_cur→EUR /
    rate_base→EUR)``.
    """
    if rates is None:
        rates = get_rates()

    base = base_of(selection)
    if base is not None:
        base_rate = _rate_to_eur(base, rates) or 1.0
        work = df_all.copy()
        factor = work["currency"].map(lambda c: _rate_to_eur(c, rates)) / base_rate
        work["amount"] = work["amount"] * factor
        work["currency"] = base
        return work, base

    return df_all[df_all["currency"] == selection].copy(), selection


def rates_editor(df_all: pd.DataFrame, key: str) -> None:
    """Render an expander to edit the manual EUR conversion rates.

    Only shown when the data spans more than one currency (otherwise there is
    nothing to convert). Exposes every currency in the data plus the combined
    target bases (USD, AED) so all the ``All → …`` views can be converted.
    """
    present = sorted(df_all["currency"].unique())
    if len(present) <= 1:
        return

    others = sorted((set(present) | set(COMBINED_BASES)) - {BASE})
    rates = get_rates()
    with st.expander("💱 Conversion rates (→ EUR)"):
        st.caption(
            "Stored relative to EUR and used for every combined **All → …** "
            "view (EUR, USD, AED). No external API — set these manually to "
            "match your bank/statement period."
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
