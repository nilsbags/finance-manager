"use client";

import { useMemo, useState, type ReactNode } from "react";
import dayjs from "dayjs";

import {
  PERIODS,
  aggregateTimeseries,
  chooseFreq,
  cumulative as accumulate,
  periodRange,
} from "@/lib/analytics";
import { baseOf, currencyOptions, currencyView, isCombined, type Rates } from "@/lib/money";
import type { Transaction } from "@/lib/types";
import { GradientAreaChart, type SeriesShow } from "./charts/GradientAreaChart";
import { RatesEditor } from "./RatesEditor";
import { Caption, MultiSelectChips, Notice, RadioPills, Select } from "./ui";

/**
 * The shared controls + gradient chart at the top of a page (the Streamlit
 * `overview_section`): period switcher, account filter and — unless the parent
 * already picked a currency, like the Dashboard does — a currency picker with
 * the rates editor.
 *
 * Renders `children(dfPeriod, currency)` below the chart, where `dfPeriod` is
 * the full transaction set filtered to the selected period, account(s) and
 * currency — ready for each page to build its own breakdowns.
 */
export function OverviewSection({
  transactions,
  show = "both",
  cumulative = false,
  currencySelection,
  rates,
  onSaveRates,
  children,
}: {
  transactions: Transaction[];
  show?: SeriesShow;
  cumulative?: boolean;
  /** When given, the picker is hidden and this selection is used (Dashboard). */
  currencySelection?: string;
  rates: Rates;
  onSaveRates: (rates: Rates) => void;
  children?: (dfPeriod: Transaction[], currency: string) => ReactNode;
}) {
  const [period, setPeriod] = useState<string>(PERIODS[0]);
  const [accounts, setAccounts] = useState<string[]>([]);
  const options = useMemo(() => currencyOptions(transactions), [transactions]);
  const [ownSelection, setOwnSelection] = useState<string | null>(null);

  const renderOwnCurrency = currencySelection === undefined;
  const selection = currencySelection ?? ownSelection ?? options[0] ?? "EUR";

  const accountOptions = useMemo(
    () => [...new Set(transactions.map((t) => t.account))].sort(),
    [transactions],
  );

  const [start, end] = periodRange(period);
  const [dfPeriod, currency] = useMemo(() => {
    const [work, cur] = currencyView(transactions, selection, rates);
    const filtered = work.filter(
      (t) =>
        t.date >= start &&
        t.date <= end &&
        (accounts.length === 0 || accounts.includes(t.account)),
    );
    return [filtered, cur] as const;
  }, [transactions, selection, rates, start, end, accounts]);

  const ts = useMemo(
    () => aggregateTimeseries(dfPeriod, chooseFreq(start, end)),
    [dfPeriod, start, end],
  );

  const relevantTotal =
    show === "spend"
      ? ts.reduce((a, p) => a + p.spend, 0)
      : show === "earn"
        ? ts.reduce((a, p) => a + p.income, 0)
        : ts.reduce((a, p) => a + p.spend + p.income, 0);

  const plotTs = cumulative ? accumulate(ts) : ts;

  const titles: Record<SeriesShow, string> = {
    spend: "Spendings",
    earn: "Earnings",
    both: "Spendings vs. earnings",
  };
  let title = titles[show];
  if (cumulative) title = `Cumulative ${title.toLowerCase()}`;
  const combinedNote = isCombined(selection) ? ` · converted to ${baseOf(selection)}` : "";

  return (
    <section>
      <div className="flex flex-wrap items-end gap-4">
        <RadioPills options={PERIODS} value={period} onChange={setPeriod} />
        {accountOptions.length > 1 && (
          <MultiSelectChips
            label="Account"
            options={accountOptions}
            selected={accounts}
            onChange={setAccounts}
          />
        )}
        {renderOwnCurrency && options.length > 1 && (
          <div className="ml-auto w-40">
            <Select label="Currency" value={selection} options={options} onChange={setOwnSelection} />
          </div>
        )}
      </div>
      {renderOwnCurrency && (
        <div className="mt-3">
          <RatesEditor transactions={transactions} rates={rates} onSave={onSaveRates} />
        </div>
      )}

      <div className="mt-3">
        <Caption>
          {title} · {period} ({dayjs(start).format("DD MMM YYYY")} –{" "}
          {dayjs(end).format("DD MMM YYYY")}){combinedNote}
        </Caption>
      </div>

      {relevantTotal === 0 ? (
        <div className="mt-3">
          <Notice>No transactions in the selected period.</Notice>
        </div>
      ) : (
        <GradientAreaChart data={plotTs} currency={currency} show={show} />
      )}

      {children?.(dfPeriod, currency)}
    </section>
  );
}
