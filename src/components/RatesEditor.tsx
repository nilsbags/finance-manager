"use client";

import { DEFAULT_RATES, editableRateCurrencies, type Rates } from "@/lib/money";
import type { Transaction } from "@/lib/types";
import { Expander, Caption, Labeled } from "./ui";

/**
 * Expander to edit the manual EUR conversion rates. Only shown when the data
 * spans more than one currency (otherwise there is nothing to convert).
 * Exposes every currency in the data plus the combined target bases (USD,
 * AED) so all the `All → …` views can be converted.
 */
export function RatesEditor({
  transactions,
  rates,
  onSave,
}: {
  transactions: Pick<Transaction, "currency">[];
  rates: Rates;
  onSave: (rates: Rates) => void;
}) {
  const currencies = editableRateCurrencies(transactions);
  if (currencies.length === 0) return null;

  return (
    <Expander title="💱 Conversion rates (→ EUR)">
      <Caption>
        Stored relative to EUR and used for every combined <b>All → …</b> view (EUR, USD,
        AED). No external API — set these manually to match your bank/statement period.
      </Caption>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {currencies.map((cur) => (
          <Labeled key={cur} label={`1 ${cur} = ? EUR`}>
            <input
              type="number"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              min={0}
              step={0.01}
              value={rates[cur] ?? DEFAULT_RATES[cur] ?? 1.0}
              onChange={(e) => {
                const value = Number(e.target.value);
                if (Number.isFinite(value) && value >= 0) {
                  onSave({ ...rates, [cur]: value });
                }
              }}
            />
          </Labeled>
        ))}
      </div>
    </Expander>
  );
}
