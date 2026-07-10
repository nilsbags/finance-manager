"use client";

import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

import { aggregateTimeseries, monthLabel, monthLabelLong, monthlyTotals } from "@/lib/analytics";
import { fmtMoney, fmtNum, fmtSigned } from "@/lib/format";
import { COMBINED_BASES, convertAmount, currencyOptions, currencyView } from "@/lib/money";
import type { AccountBalance } from "@/lib/types";
import { GradientAreaChart } from "@/components/charts/GradientAreaChart";
import { GroupedBarChart } from "@/components/charts/GroupedBarChart";
import { RatesEditor } from "@/components/RatesEditor";
import { useFinanceData } from "@/components/useFinanceData";
import { Caption, MetricCard, Notice, PageTitle, SectionTitle, Select } from "@/components/ui";

interface MonthlyRow {
  month: string; // YYYY-MM
  spend: number;
  income: number;
  net: number;
  savingsRate: number | null;
  count: number;
}

export default function DashboardPage() {
  const { transactions, rates, saveRates, loading } = useFinanceData();
  const [balances, setBalances] = useState<AccountBalance[]>([]);
  const [selection, setSelection] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/balances")
      .then((r) => r.json())
      .then(setBalances);
  }, []);

  const all = useMemo(() => transactions ?? [], [transactions]);
  const options = useMemo(() => currencyOptions(all), [all]);
  const sel = selection ?? options[0] ?? "EUR";

  const [curDf, currency] = useMemo(() => currencyView(all, sel, rates), [all, sel, rates]);

  // Per-month spendings / earnings / net / savings rate / count, newest first.
  const monthlyRows = useMemo<MonthlyRow[]>(() => {
    const map = new Map<string, { spend: number; income: number; count: number }>();
    for (const t of curDf) {
      const m = t.date.slice(0, 7);
      const e = map.get(m) ?? { spend: 0, income: 0, count: 0 };
      if (t.amount < 0) e.spend += -t.amount;
      else if (t.amount > 0) e.income += t.amount;
      e.count += 1;
      map.set(m, e);
    }
    return [...map.entries()]
      .map(([month, v]) => ({
        month,
        spend: v.spend,
        income: v.income,
        net: v.income - v.spend,
        savingsRate: v.income > 0 ? ((v.income - v.spend) / v.income) * 100 : null,
        count: v.count,
      }))
      .sort((a, b) => b.month.localeCompare(a.month));
  }, [curDf]);

  const byMonth = useMemo(() => new Map(monthlyRows.map((r) => [r.month, r])), [monthlyRows]);

  // The chart follows the table selection; default to the newest month with data.
  const effectiveMonth = selectedMonth ?? monthlyRows[0]?.month ?? dayjs().format("YYYY-MM");

  // --- KPI cards: this calendar month vs last (independent of the selection). #
  const thisMonth = dayjs().format("YYYY-MM");
  const lastMonth = dayjs().subtract(1, "month").format("YYYY-MM");
  const kThis = byMonth.get(thisMonth);
  const kLast = byMonth.get(lastMonth);
  const hasPrev = byMonth.has(lastMonth);

  const spendNow = kThis?.spend ?? 0;
  const spendPrev = kLast?.spend ?? 0;
  const earnNow = kThis?.income ?? 0;
  const earnPrev = kLast?.income ?? 0;
  const netNow = earnNow - spendNow;
  const netPrev = earnPrev - spendPrev;
  const srNow = earnNow > 0 ? (netNow / earnNow) * 100 : null;
  const srPrev = earnPrev > 0 ? (netPrev / earnPrev) * 100 : null;

  const moneyDelta = (now: number, prev: number) =>
    hasPrev ? `${fmtSigned(now - prev)} ${currency}` : null;

  // Grouped bar chart across all months (ascending).
  const monthlyAsc = useMemo(() => monthlyTotals(curDf), [curDf]);

  // Daily spendings & earnings for the selected month.
  const monthSeries = useMemo(() => {
    const monthTx = curDf.filter((t) => t.date.slice(0, 7) === effectiveMonth);
    return aggregateTimeseries(monthTx, "D");
  }, [curDf, effectiveMonth]);

  if (loading) return <PageTitle>📊 Dashboard</PageTitle>;

  return (
    <div>
      <PageTitle>📊 Dashboard</PageTitle>

      {/* Current balance (one total, shown in each currency) */}
      {balances.length > 0 && (
        <>
          <SectionTitle>💰 Current balance</SectionTitle>
          <div className="grid gap-4 sm:grid-cols-3">
            {COMBINED_BASES.map((base) => {
              const total = balances.reduce(
                (acc, b) => acc + convertAmount(b.balance, b.currency, base, rates),
                0,
              );
              return <MetricCard key={base} label={base} value={fmtMoney(total, base)} />;
            })}
          </div>
        </>
      )}

      {all.length === 0 ? (
        <div className="mt-6">
          <Notice>
            No transactions yet. Import a CSV on the <b>Import</b> page first.
          </Notice>
        </div>
      ) : (
        <>
          {/* Currency (picked once for the whole page) */}
          <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">{dayjs().format("MMMM YYYY")} · overview</h2>
              <Caption>Big numbers are this month; deltas compare with last month.</Caption>
            </div>
            {options.length > 1 && (
              <div className="w-44">
                <Select label="Currency" value={sel} options={options} onChange={setSelection} />
              </div>
            )}
          </div>
          <div className="mt-3">
            <RatesEditor transactions={all} rates={rates} onSave={saveRates} />
          </div>

          {/* Big KPI cards */}
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Spendings"
              value={fmtMoney(spendNow, currency)}
              delta={moneyDelta(spendNow, spendPrev)}
              deltaColor="inverse"
            />
            <MetricCard
              label="Earnings"
              value={fmtMoney(earnNow, currency)}
              delta={moneyDelta(earnNow, earnPrev)}
            />
            <MetricCard
              label="Net"
              value={fmtMoney(netNow, currency)}
              delta={moneyDelta(netNow, netPrev)}
            />
            <MetricCard
              label="Savings rate"
              value={srNow !== null ? `${fmtNum(srNow)}%` : "—"}
              delta={
                hasPrev && srNow !== null && srPrev !== null
                  ? `${fmtSigned(srNow - srPrev)} pp`
                  : null
              }
            />
          </div>

          {/* Month-over-month comparison */}
          <SectionTitle>Spendings vs. earnings by month</SectionTitle>
          {monthlyAsc.length <= 1 ? (
            <Caption>Not enough months of data yet to compare.</Caption>
          ) : (
            <GroupedBarChart byMonth={monthlyAsc} currency={currency} />
          )}

          {/* Selected month's spendings & earnings */}
          <SectionTitle>Spendings &amp; earnings — {monthLabelLong(effectiveMonth)}</SectionTitle>
          {monthSeries.length === 0 ? (
            <Caption>No transactions in {monthLabelLong(effectiveMonth)}.</Caption>
          ) : (
            <GradientAreaChart data={monthSeries} currency={currency} show="both" />
          )}

          {/* Monthly breakdown table (drives the chart above) */}
          <SectionTitle>Monthly breakdown</SectionTitle>
          <Caption>Select a month to see its spendings and earnings in the chart above.</Caption>
          <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2">Month</th>
                  <th className="px-4 py-2 text-right">Spendings ({currency})</th>
                  <th className="px-4 py-2 text-right">Earnings ({currency})</th>
                  <th className="px-4 py-2 text-right">Net ({currency})</th>
                  <th className="px-4 py-2 text-right">Savings rate</th>
                  <th className="px-4 py-2 text-right">Transactions</th>
                </tr>
              </thead>
              <tbody>
                {monthlyRows.map((row) => {
                  const selectedRow = row.month === effectiveMonth;
                  return (
                    <tr
                      key={row.month}
                      onClick={() => setSelectedMonth(row.month)}
                      className={`cursor-pointer border-b border-slate-100 last:border-0 dark:border-slate-800 ${
                        selectedRow
                          ? "bg-slate-100 font-medium dark:bg-slate-800"
                          : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                      }`}
                    >
                      <td className="whitespace-nowrap px-4 py-2">{monthLabel(row.month)}</td>
                      <td className="px-4 py-2 text-right text-red-600 dark:text-red-400">
                        {fmtNum(row.spend, 2)}
                      </td>
                      <td className="px-4 py-2 text-right text-green-600 dark:text-green-400">
                        {fmtNum(row.income, 2)}
                      </td>
                      <td
                        className={`px-4 py-2 text-right ${
                          row.net < 0
                            ? "text-red-600 dark:text-red-400"
                            : "text-green-600 dark:text-green-400"
                        }`}
                      >
                        {fmtNum(row.net, 2)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {row.savingsRate !== null ? `${fmtNum(row.savingsRate)}%` : "—"}
                      </td>
                      <td className="px-4 py-2 text-right">{row.count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
