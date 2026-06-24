"""Category rule engine.

A rule is a case-insensitive substring match against a transaction's
description, mapping to a ``(category, subcategory)`` pair — e.g. pattern
``BILLA`` -> ``("Food & Drink", "Groceries")``. Rules are applied in insertion
order; the first match wins.
"""

import database

# A loaded rule: (lowercased pattern, category, subcategory), in priority order.
type Rule = tuple[str, str, str]


def load_rules() -> list[Rule]:
    """Return rules as ``(pattern_lower, category, subcategory)`` tuples."""
    return [
        (row["pattern"].lower(), row["category"], row["subcategory"] or "")
        for row in database.fetch_rules()
    ]


def categorize(description: str, rules: list[Rule] | None = None) -> tuple[str, str] | None:
    """Return ``(category, subcategory)`` for a description, or ``None``."""
    if rules is None:
        rules = load_rules()
    text = (description or "").lower()
    for pattern, category, subcategory in rules:
        if pattern and pattern in text:
            return category, subcategory
    return None


def apply_rules_to_existing(only_uncategorized: bool = True) -> int:
    """Re-run rules over stored transactions and update their categories.

    When ``only_uncategorized`` is True, transactions that already have a
    category other than the default bucket are left untouched. Returns the
    number of transactions whose category/subcategory changed.
    """
    rules = load_rules()
    if not rules:
        return 0

    df = database.fetch_transactions()
    if df.empty:
        return 0

    changed = 0
    for _, row in df.iterrows():
        if only_uncategorized and row["category"] != database.UNCATEGORIZED:
            continue
        match = categorize(row["description"], rules)
        if not match:
            continue
        category, subcategory = match
        if category != row["category"] or subcategory != (row["subcategory"] or ""):
            database.set_category(int(row["id"]), category, subcategory)
            changed += 1
    return changed
