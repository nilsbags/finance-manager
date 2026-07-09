/**
 * CSV value parsing and column auto-detection (pure — used by the Import page
 * in the browser and by the import API on the server).
 */

import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";

dayjs.extend(customParseFormat);

// Matches an unambiguous ISO-8601 style date (YYYY-MM-DD). For these we must
// NOT apply the `dayfirst` heuristic, or month and day get silently swapped
// (e.g. 2026-02-06 -> 2 June 2026).
const ISO_DATE_RE = /^\s*\d{4}-\d{1,2}-\d{1,2}/;

// Logical fields the app understands. `account` and `currency` may be supplied
// either as a CSV column or as a single constant value entered in the UI.
// `balance` is optional and only used to deduce unlisted income.
export const REQUIRED_FIELDS = ["date", "description", "amount"] as const;
export const OPTIONAL_FIELDS = ["account", "currency", "balance"] as const;

/**
 * Parse a single amount cell into a number, or `null` if unparseable.
 *
 * Handles thousands separators and the European "comma as decimal point"
 * convention (e.g. `1.234,56` -> `1234.56`).
 */
export function parseAmount(value: unknown, decimalComma = false): number | null {
  if (value === null || value === undefined) return null;
  let text = String(value).trim();
  if (text === "" || text.toLowerCase() === "nan") return null;

  // Normalise common currency noise.
  text = text.replace(/ /g, "").replace(/ /g, "");
  text = text.replace(/€/g, "").replace(/\$/g, "").replace(/£/g, "");

  if (decimalComma) {
    // 1.234,56 -> 1234.56
    text = text.replace(/\./g, "").replace(/,/g, ".");
  } else {
    // 1,234.56 -> 1234.56
    text = text.replace(/,/g, "");
  }

  // Reject anything Number() would only partially understand (e.g. "12abc").
  if (!/^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/.test(text)) return null;
  const num = Number(text);
  return Number.isFinite(num) ? num : null;
}

// Candidate formats tried in strict order. Day-first vs month-first only
// changes which ambiguous set is preferred; the other still acts as fallback
// (e.g. "12/31/2025" parses as Dec 31 even in day-first mode, since day 31
// cannot be a month).
// NB: dayjs strict parsing requires an exact round-trip, so zero-padded
// values only match double-letter tokens — both variants must be listed.
const DAYFIRST_FORMATS = [
  "DD/MM/YYYY", "D/M/YYYY", "DD.MM.YYYY", "D.M.YYYY", "DD-MM-YYYY", "D-M-YYYY",
  "DD/MM/YY", "D/M/YY", "DD.MM.YY", "D.M.YY", "DD-MM-YY", "D-M-YY",
  "D MMM YYYY", "DD MMM YYYY", "D MMMM YYYY",
];
const MONTHFIRST_FORMATS = [
  "MM/DD/YYYY", "M/D/YYYY", "MM.DD.YYYY", "M.D.YYYY", "MM-DD-YYYY", "M-D-YYYY",
  "MM/DD/YY", "M/D/YY", "MM.DD.YY", "M.D.YY", "MM-DD-YY", "M-D-YY",
  "MMM D YYYY", "MMM D, YYYY", "MMMM D, YYYY",
];
const COMMON_FORMATS = ["YYYY/MM/DD", "YYYY/M/D", "YYYYMMDD", "YYYY-MM-DD HH:mm:ss"];

/**
 * Parse a date cell into an ISO `YYYY-MM-DD` string, or `null`.
 *
 * `dayfirst` only applies to ambiguous formats such as `31/12/2025`;
 * already-ISO values are parsed verbatim so month and day are never swapped.
 */
export function parseDate(value: unknown, dayfirst = true): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (text === "" || text.toLowerCase() === "nan") return null;

  let parsed: dayjs.Dayjs | null = null;
  if (ISO_DATE_RE.test(text)) {
    parsed = dayjs(text);
  } else {
    const preferred = dayfirst ? DAYFIRST_FORMATS : MONTHFIRST_FORMATS;
    const fallback = dayfirst ? MONTHFIRST_FORMATS : DAYFIRST_FORMATS;
    // Try formats one at a time: dayjs given an *array* does not honour array
    // order, which would break the day-first preference for ambiguous dates.
    for (const format of [...preferred, ...fallback, ...COMMON_FORMATS]) {
      const attempt = dayjs(text, format, true);
      if (attempt.isValid()) {
        parsed = attempt;
        break;
      }
    }
    if (parsed === null) parsed = dayjs(text); // last-resort loose parse
  }
  return parsed.isValid() ? parsed.format("YYYY-MM-DD") : null;
}

/**
 * Best-matching column index for a required field, given ranked name aliases.
 *
 * Scoring prefers an exact name match, then "starts with", then "contains",
 * so e.g. a real `Description` column beats `Account name` for the
 * description field. Returns 0 when nothing matches at all.
 */
export function guessColumn(columns: string[], aliases: string[]): number {
  let bestI = 0;
  let bestScore = 0;
  columns.forEach((col, i) => {
    const name = col.toLowerCase().trim();
    let score = 0;
    aliases.forEach((alias, rank) => {
      const penalty = rank; // earlier aliases are stronger signals
      if (name === alias) score = Math.max(score, 100 - penalty);
      else if (name.startsWith(alias)) score = Math.max(score, 60 - penalty);
      else if (name.includes(alias)) score = Math.max(score, 30 - penalty);
    });
    if (score > bestScore) {
      bestI = i;
      bestScore = score;
    }
  });
  return bestI;
}

/**
 * Like `guessColumn` but for optional fields: returns the matching column
 * name, or `null` when no column is a clear match (── not in file ──).
 */
export function guessOptionalColumn(columns: string[], aliases: string[]): string | null {
  let best: string | null = null;
  let bestScore = 0;
  columns.forEach((col) => {
    const name = col.toLowerCase().trim();
    aliases.forEach((alias, rank) => {
      let score: number;
      if (name === alias) score = 100 - rank;
      else if (name.startsWith(alias)) score = 60 - rank;
      else if (name.includes(alias)) score = 30 - rank;
      else return;
      if (score > bestScore) {
        best = col;
        bestScore = score;
      }
    });
  });
  return best;
}

/** First `limit` non-empty string values of a column. */
function sample(values: unknown[], limit = 300): string[] {
  const out: string[] = [];
  for (const v of values) {
    if (v === null || v === undefined) continue;
    const s = String(v).trim();
    if (s && s.toLowerCase() !== "nan") out.push(s);
    if (out.length >= limit) break;
  }
  return out;
}

/**
 * Guess whether a date column is day-first, adapting to the file.
 *
 * ISO `YYYY-MM-DD` dates are not day-first. For `D/M/Y` vs `M/D/Y` we
 * disambiguate using any component > 12 (a 13+ in the first slot means
 * day-first; in the second slot means month-first). Falls back to the
 * European convention (day-first) when it's genuinely ambiguous.
 */
export function detectDayfirst(values: unknown[], fallback = true): boolean {
  const vals = sample(values);
  if (vals.length === 0) return fallback;
  const iso = vals.filter((v) => /^\d{4}-\d{1,2}-\d{1,2}/.test(v)).length;
  if (iso / vals.length >= 0.6) return false;
  let firstGt12 = 0;
  let secondGt12 = 0;
  for (const v of vals) {
    const m = v.match(/^(\d{1,2})[./-](\d{1,2})[./-]\d{2,4}/);
    if (m) {
      firstGt12 += Number(m[1]) > 12 ? 1 : 0;
      secondGt12 += Number(m[2]) > 12 ? 1 : 0;
    }
  }
  if (firstGt12 > secondGt12) return true;
  if (secondGt12 > firstGt12) return false;
  return fallback;
}

/** Guess whether amounts use a comma decimal separator (e.g. 1.234,56). */
export function detectDecimalComma(values: unknown[]): boolean {
  const vals = sample(values);
  let comma = 0;
  let total = 0;
  for (const v of vals) {
    const lastDot = v.lastIndexOf(".");
    const lastComma = v.lastIndexOf(",");
    if (lastDot === -1 && lastComma === -1) continue;
    total += 1;
    comma += lastComma > lastDot ? 1 : 0;
  }
  return total > 0 && comma / total >= 0.5;
}
