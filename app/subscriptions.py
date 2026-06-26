"""Detect recurring *monthly* charges (subscriptions) from transactions.

The heuristic groups expenses by a normalised merchant name (per currency) and
keeps the groups that look like a subscription:

* charged at least ``min_occurrences`` times,
* with a roughly **monthly** cadence (median gap between charges within the
  ``min_gap_days`` … ``max_gap_days`` window), and
* with **consistent amounts** (coefficient of variation below ``max_amount_cv``),
  which weeds out variable spend like restaurants or ride-hailing.

Only monthly (or longer) cadences are considered subscriptions: any merchant
that recurs faster than monthly — weekly, biweekly, … — is rejected, even when
it falls in a subscription-type category. The one exception is an explicit name
match (e.g. "Claude ai subscription"): a name that literally says "subscription"
is trusted and counted regardless of cadence, even bursty same-week charges.

This is intentionally simple and explainable — no external services.
"""

import re

import pandas as pd

# Defaults tuned for monthly billing with a little slack for billing-day drift.
DEFAULT_MIN_OCCURRENCES = 2
DEFAULT_MIN_GAP_DAYS = 21
DEFAULT_MAX_GAP_DAYS = 40
DEFAULT_MAX_AMOUNT_CV = 0.30

# Subcategories that are subscriptions by nature, so a recurring merchant in one
# of these counts even when the sampled cadence looks irregular (real-world
# statements often bill in bursts or only cover a few months).
SUBSCRIPTION_SUBCATEGORIES = {
    "Software & Subscriptions",
    "Streaming",
    "Phone & Internet",
}

# Merchant names containing one of these words are treated as a subscription
# signal too — e.g. "Claude Subscription" — even outside the categories above.
SUBSCRIPTION_NAME_KEYWORDS = ("subscription",)


def _name_signals_subscription(merchant_key: str) -> bool:
    """True if the (normalised) merchant name itself says it's a subscription."""
    return any(kw in merchant_key for kw in SUBSCRIPTION_NAME_KEYWORDS)


def normalize_merchant(description: str) -> str:
    """Collapse a description to a stable merchant key (letters only, lowered)."""
    s = (description or "").lower()
    s = re.sub(r"[0-9]+", " ", s)        # drop reference numbers
    s = re.sub(r"[^a-z\s]", " ", s)      # drop punctuation/symbols
    s = re.sub(r"\s+", " ", s).strip()
    return s


_COLUMNS = [
    "merchant", "category", "subcategory", "currency", "typical_amount",
    "occurrences", "median_gap_days", "amount_cv", "first_seen", "last_seen",
    "active", "confidence",
]


def detect(
    df: pd.DataFrame,
    *,
    min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
    min_gap_days: int = DEFAULT_MIN_GAP_DAYS,
    max_gap_days: int = DEFAULT_MAX_GAP_DAYS,
    max_amount_cv: float = DEFAULT_MAX_AMOUNT_CV,
    active_within_days: int = 45,
    include_category_matches: bool = True,
) -> pd.DataFrame:
    """Return detected recurring subscriptions, one row per merchant.

    A merchant qualifies if it recurs (``>= min_occurrences``) and EITHER:

    * (when ``include_category_matches``) its name says it's a subscription
      (see :data:`SUBSCRIPTION_NAME_KEYWORDS`, e.g. "Claude ai subscription") —
      this trusted signal counts regardless of cadence, OR
    * it is not faster than monthly AND it either shows a roughly monthly
      cadence with consistent amounts, or (when ``include_category_matches``)
      sits in an inherently subscription category (see
      :data:`SUBSCRIPTION_SUBCATEGORIES`).

    A ``confidence`` of *High* is assigned to subscription-signalled merchants
    and near-constant amounts; everything else is *Medium*. Columns:
    merchant, category, subcategory, currency, typical_amount, occurrences,
    median_gap_days, amount_cv, first_seen, last_seen, active, confidence.
    """
    empty = pd.DataFrame(columns=_COLUMNS)
    if df.empty:
        return empty

    exp = df[df["amount"] < 0].copy()
    if exp.empty:
        return empty

    exp["merchant_key"] = exp["description"].map(normalize_merchant)
    exp["abs_amount"] = exp["amount"].abs()
    reference_date = exp["date"].max()

    rows: list[dict] = []
    for (merchant_key, currency), group in exp.groupby(["merchant_key", "currency"]):
        if len(group) < min_occurrences:
            continue

        group = group.sort_values("date")
        gaps = group["date"].diff().dropna().dt.days
        median_gap = float(gaps.median()) if not gaps.empty else 0.0

        amounts = group["abs_amount"]
        mean_amount = amounts.mean()
        cv = float(amounts.std(ddof=0) / mean_amount) if mean_amount else 0.0
        subcategory = group["subcategory"].mode().iat[0] or ""

        is_sub_category = subcategory in SUBSCRIPTION_SUBCATEGORIES
        is_sub_name = _name_signals_subscription(merchant_key)
        is_sub_signal = is_sub_category or is_sub_name
        has_monthly_cadence = (
            (min_gap_days <= median_gap <= max_gap_days) and cv <= max_amount_cv
        )
        sub_monthly = (not gaps.empty) and (median_gap < min_gap_days)

        # An explicit name match (e.g. "Claude ai subscription") is a strong,
        # user-trusted signal: count it regardless of cadence — even when the
        # charges land in a tight burst. Otherwise enforce "monthly or longer":
        # anything faster than monthly (weekly, biweekly, …) is not a
        # subscription, even in a subscription-type category.
        if include_category_matches and is_sub_name:
            qualifies = True
        elif sub_monthly:
            qualifies = False
        else:
            qualifies = has_monthly_cadence or (
                include_category_matches and is_sub_category
            )

        if not qualifies:
            continue

        last_seen = group["date"].max()
        confidence = "High" if (is_sub_signal or cv <= 0.15) else "Medium"
        rows.append(
            {
                "merchant": group["description"].mode().iat[0],
                "category": group["category"].mode().iat[0],
                "subcategory": subcategory,
                "currency": currency,
                "typical_amount": float(amounts.median()),
                "occurrences": int(len(group)),
                "median_gap_days": round(median_gap),
                "amount_cv": cv,
                "first_seen": group["date"].min(),
                "last_seen": last_seen,
                "active": (reference_date - last_seen).days <= active_within_days,
                "confidence": confidence,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return empty
    return result.sort_values("typical_amount", ascending=False).reset_index(drop=True)
