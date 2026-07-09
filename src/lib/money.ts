/**
 * Currency handling: combined "All → <currency>" views with manual FX rates.
 *
 * The app is local-first with no external API, so exchange rates are entered
 * by hand and stored in the `meta` table (via the /api/rates route). Rates are
 * stored relative to a single pivot (EUR); conversions into any other target
 * base are derived from them. `currencyView` turns a currency *selection*
 * (a single code, or one of the combined `All → …` options) into a working
 * list whose `amount` is expressed in the display currency.
 *
 * Pure — safe to use on client and server.
 */

import type { Transaction } from "./types";

// Pivot currency the stored rates are expressed against (1 unit = N EUR).
export const BASE = "EUR";

// Target bases offered as combined "All → …" views, in display order. EUR is
// first so it is the default selection in every currency picker.
export const COMBINED_BASES = ["EUR", "USD", "AED"] as const;

// Meta key the manual rates are persisted under (same as the Python app).
export const FX_META_KEY = "fx_rates_to_eur";

/** Human label for a combined view into `base` (e.g. `"All → USD"`). */
export function combinedLabel(base: string): string {
  return `All → ${base}`;
}

export const COMBINED_LABELS: string[] = COMBINED_BASES.map(combinedLabel);
const BASE_BY_LABEL: Record<string, string> = Object.fromEntries(
  COMBINED_BASES.map((b) => [combinedLabel(b), b]),
);

// Sensible starting rates (1 unit of currency = N EUR). User-editable in the UI.
export const DEFAULT_RATES: Record<string, number> = {
  EUR: 1.0,
  USD: 0.92,
  AED: 0.25,
  GBP: 1.17,
  CHF: 1.06,
};

export type Rates = Record<string, number>;

/** True if `selection` is one of the combined "All → …" options. */
export function isCombined(selection: string): boolean {
  return selection in BASE_BY_LABEL;
}

/** Target currency code for a combined selection, else `null`. */
export function baseOf(selection: string): string | null {
  return BASE_BY_LABEL[selection] ?? null;
}

/**
 * Currency picker options for a set of transactions.
 *
 * With more than one currency the combined "All → …" views come first (EUR
 * leading, so it is the default), followed by each individual currency.
 */
export function currencyOptions(transactions: Pick<Transaction, "currency">[]): string[] {
  const curs = [...new Set(transactions.map((t) => t.currency))].sort();
  return curs.length > 1 ? [...COMBINED_LABELS, ...curs] : curs;
}

function rateToEur(cur: string, rates: Rates): number {
  return rates[cur] ?? DEFAULT_RATES[cur] ?? 1.0;
}

/** Convert a single amount between currencies via the EUR pivot rates. */
export function convertAmount(amount: number, fromCur: string, toCur: string, rates: Rates): number {
  if (fromCur === toCur) return amount;
  return amount * (rateToEur(fromCur, rates) / (rateToEur(toCur, rates) || 1.0));
}

/**
 * Return `[workingRows, displayCurrency]` for a currency selection.
 *
 * For a single currency this is just a filtered copy. For a combined
 * `All → <base>` view every row's amount is converted into `base` and the
 * currency field is normalised, so downstream aggregation simply works.
 */
export function currencyView<T extends Pick<Transaction, "amount" | "currency">>(
  rows: T[],
  selection: string,
  rates: Rates,
): [T[], string] {
  const base = baseOf(selection);
  if (base !== null) {
    const baseRate = rateToEur(base, rates) || 1.0;
    const work = rows.map((r) => ({
      ...r,
      amount: r.amount * (rateToEur(r.currency, rates) / baseRate),
      currency: base,
    }));
    return [work, base];
  }
  return [rows.filter((r) => r.currency === selection), selection];
}

/**
 * The currencies whose rate is editable for a data set: every currency present
 * plus the combined target bases (USD, AED), minus the EUR pivot itself.
 * Empty when the data spans at most one currency (nothing to convert).
 */
export function editableRateCurrencies(transactions: Pick<Transaction, "currency">[]): string[] {
  const present = [...new Set(transactions.map((t) => t.currency))];
  if (present.length <= 1) return [];
  return [...new Set([...present, ...COMBINED_BASES])].filter((c) => c !== BASE).sort();
}
