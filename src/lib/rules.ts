/**
 * Category rule engine (pure — safe to use on client and server).
 *
 * A rule is a case-insensitive substring match against a transaction's
 * description, mapping to a `[category, subcategory]` pair — e.g. pattern
 * `BILLA` -> `["Food & Drink", "Groceries"]`. Rules are applied in insertion
 * order; the first match wins.
 */

/** A loaded rule: [lowercased pattern, category, subcategory], in priority order. */
export type Rule = [string, string, string];

/** Return `[category, subcategory]` for a description, or `null`. */
export function categorize(description: string, rules: Rule[]): [string, string] | null {
  const text = (description || "").toLowerCase();
  for (const [pattern, category, subcategory] of rules) {
    if (pattern && text.includes(pattern)) return [category, subcategory];
  }
  return null;
}
