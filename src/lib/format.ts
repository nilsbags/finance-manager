/** Number formatting shared across pages (matches the Python `:,` style). */

export function fmtNum(n: number, decimals = 0): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtMoney(n: number, currency: string, decimals = 0): string {
  return `${fmtNum(n, decimals)} ${currency}`;
}

/** Signed value, e.g. "+1,234" / "-1,234" (used for month-over-month deltas). */
export function fmtSigned(n: number, decimals = 0): string {
  const sign = n >= 0 ? "+" : "-";
  return `${sign}${fmtNum(Math.abs(n), decimals)}`;
}

// Colour palette shared across pages (RGB triples reused for line + gradient).
export const SPEND_RGB = "239, 68, 68"; // red
export const EARN_RGB = "34, 197, 94"; // green
