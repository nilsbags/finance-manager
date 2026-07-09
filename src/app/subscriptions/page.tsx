"use client";

import { useMemo, useState } from "react";

import { colorFor } from "@/lib/categories";
import { fmtNum } from "@/lib/format";
import {
  DEFAULT_MAX_AMOUNT_CV,
  DEFAULT_MIN_OCCURRENCES,
  detect,
} from "@/lib/subscriptions";
import { HBarChart } from "@/components/charts/HBarChart";
import { RatesEditor } from "@/components/RatesEditor";
import { useFinanceData } from "@/components/useFinanceData";
import {
  Caption,
  Checkbox,
  Expander,
  MetricCard,
  Notice,
  PageTitle,
  SectionTitle,
  Slider,
  Toggle,
} from "@/components/ui";

export default function SubscriptionsPage() {
  const { transactions, rates, saveRates, loading } = useFinanceData();
  const all = useMemo(() => transactions ?? [], [transactions]);

  // Detection settings.
  const [minOcc, setMinOcc] = useState(DEFAULT_MIN_OCCURRENCES);
  const [maxCv, setMaxCv] = useState(DEFAULT_MAX_AMOUNT_CV);
  const [includeCat, setIncludeCat] = useState(true);
  const [highOnly, setHighOnly] = useState(true);
  const [showInactive, setShowInactive] = useState(true);

  const subs = useMemo(() => {
    let detected = detect(all, {
      minOccurrences: minOcc,
      maxAmountCv: maxCv,
      includeCategoryMatches: includeCat,
    });
    if (highOnly) detected = detected.filter((s) => s.confidence === "High");
    if (!showInactive) detected = detected.filter((s) => s.active);
    // Convert each subscription's typical amount to EUR for comparable totals.
    return detected.map((s) => {
      const monthlyEur = s.typicalAmount * (rates[s.currency] ?? 1.0);
      return { ...s, monthlyEur, annualEur: monthlyEur * 12 };
    });
  }, [all, minOcc, maxCv, includeCat, highOnly, showInactive, rates]);

  const active = subs.filter((s) => s.active);

  if (loading) return <PageTitle>🔁 Monthly subscriptions</PageTitle>;

  if (all.length === 0) {
    return (
      <div>
        <PageTitle>🔁 Monthly subscriptions</PageTitle>
        <div className="mt-4">
          <Notice>
            No transactions yet. Import a CSV on the <b>Import</b> page first.
          </Notice>
        </div>
      </div>
    );
  }

  const top = [...active].sort((a, b) => b.annualEur - a.annualEur)[0];

  return (
    <div>
      <PageTitle>🔁 Monthly subscriptions</PageTitle>
      <Caption>
        Recurring charges detected from your transactions — review them and cancel what you no
        longer use to save money.
      </Caption>

      {/* Detection settings */}
      <div className="mt-6">
        <Expander title="Detection settings">
          <div className="grid gap-4 sm:grid-cols-3">
            <Slider label="Minimum charges" value={minOcc} min={2} max={6} onChange={setMinOcc} />
            <Slider
              label="Max amount variation"
              value={maxCv}
              min={0}
              max={1}
              step={0.05}
              onChange={setMaxCv}
              help="Lower = stricter (amounts must be more consistent)."
            />
            <Checkbox
              label="Include subscription-type categories & names"
              checked={includeCat}
              onChange={setIncludeCat}
              help="Count merchants in Software & Subscriptions, Streaming, Phone & Internet — or whose name contains 'subscription' (e.g. 'Claude Subscription') — even when the cadence is irregular, as long as it stays monthly or longer (weekly/shorter charges are never counted)."
            />
          </div>
          <div className="mt-3">
            <Caption>Conversion rates below are used for the combined EUR totals.</Caption>
            <div className="mt-2">
              <RatesEditor transactions={all} rates={rates} onSave={saveRates} />
            </div>
          </div>
        </Expander>
      </div>

      <div className="mt-4 flex flex-wrap gap-6">
        <Toggle
          label="Likely subscriptions only (High confidence)"
          checked={highOnly}
          onChange={setHighOnly}
        />
        <Toggle label="Show inactive" checked={showInactive} onChange={setShowInactive} />
      </div>

      {subs.length === 0 ? (
        <div className="mt-6">
          <Notice>
            No recurring monthly charges detected with the current settings. Try lowering the
            minimum charges or raising the amount-variation limit.
          </Notice>
        </div>
      ) : (
        <>
          {/* Summary metrics */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Subscriptions" value={String(subs.length)} />
            <MetricCard label="Active" value={String(active.length)} />
            <MetricCard
              label="Monthly (active)"
              value={`€${fmtNum(active.reduce((a, s) => a + s.monthlyEur, 0))}`}
            />
            <MetricCard
              label="Per year (active)"
              value={`€${fmtNum(active.reduce((a, s) => a + s.annualEur, 0))}`}
            />
          </div>
          <div className="mt-2">
            <Caption>
              Totals are converted to EUR using your manual rates. &lsquo;Active&rsquo; means
              charged within the last ~45 days of your data.
            </Caption>
          </div>

          {/* Savings chart: biggest subscriptions by yearly cost */}
          <SectionTitle>Where your subscription money goes (per year)</SectionTitle>
          <HBarChart
            items={subs.slice(0, 15).map((s) => ({
              label: s.merchant,
              value: s.annualEur,
              color: colorFor(s.category),
            }))}
            valueLabel="Per year (€)"
            minHeight={280}
            perBarHeight={34}
            decimals={0}
          />

          {/* Detailed list */}
          <SectionTitle>All detected subscriptions</SectionTitle>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Merchant</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2 text-right">Typical charge</th>
                  <th className="px-3 py-2 text-right">Monthly (€)</th>
                  <th className="px-3 py-2 text-right">Per year (€)</th>
                  <th className="px-3 py-2 text-right">Charges</th>
                  <th className="px-3 py-2 text-right">Every ~days</th>
                  <th className="px-3 py-2">Last charge</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {subs.map((s) => (
                  <tr key={`${s.merchant} ${s.currency}`} className="border-b border-slate-100 last:border-0">
                    <td className="max-w-xs truncate px-3 py-1.5" title={s.merchant}>
                      {s.merchant}
                    </td>
                    <td className="whitespace-nowrap px-3 py-1.5">
                      {s.subcategory ? `${s.category} › ${s.subcategory}` : s.category}
                    </td>
                    <td className="whitespace-nowrap px-3 py-1.5 text-right">
                      {fmtNum(s.typicalAmount, 2)} {s.currency}
                    </td>
                    <td className="px-3 py-1.5 text-right">€{fmtNum(s.monthlyEur, 2)}</td>
                    <td className="px-3 py-1.5 text-right">€{fmtNum(s.annualEur)}</td>
                    <td className="px-3 py-1.5 text-right">{s.occurrences}</td>
                    <td className="px-3 py-1.5 text-right">{s.medianGapDays}</td>
                    <td className="whitespace-nowrap px-3 py-1.5">{s.lastSeen}</td>
                    <td className="whitespace-nowrap px-3 py-1.5">
                      {s.active ? "🟢 Active" : "⚪ Inactive"}
                    </td>
                    <td className="px-3 py-1.5">{s.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* A nudge toward savings */}
          {top && (
            <div className="mt-6">
              <Notice>
                💡 Your most expensive active subscription is <b>{top.merchant}</b> at about{" "}
                <b>€{fmtNum(top.annualEur)}/year</b>. Cancelling the subscriptions you don&apos;t
                use could save up to{" "}
                <b>€{fmtNum(active.reduce((a, s) => a + s.annualEur, 0))}/year</b>.
              </Notice>
            </div>
          )}
        </>
      )}
    </div>
  );
}
