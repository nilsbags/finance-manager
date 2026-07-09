"use client";

import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

import { categoryBreakdown, monthlyTotals } from "@/lib/analytics";
import { fmtMoney, fmtNum, fmtSigned } from "@/lib/format";
import { COMBINED_BASES, convertAmount, currencyOptions, currencyView } from "@/lib/money";
import type { AccountBalance } from "@/lib/types";
import { HierarchyChart } from "@/components/charts/HierarchyChart";
import { GroupedBarChart } from "@/components/charts/GroupedBarChart";
import { OverviewSection } from "@/components/OverviewSection";
import { RatesEditor } from "@/components/RatesEditor";
import { useFinanceData } from "@/components/useFinanceData";
import {
  Caption,
  Card,
  MetricCard,
  Notice,
  PageTitle,
  SectionTitle,
  Select,
} from "@/components/ui";

export default function DashboardPage() {
  const { transactions, rates, saveRates, loading } = useFinanceData();
  const [balances, setBalances] = useState<AccountBalance[]>([]);
  const [selection, setSelection] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/balances")
      .then((r) => r.json())
      .then(setBalances);
  }, []);

  const all = useMemo(() => transactions ?? [], [transactions]);
  const options = useMemo(() => currencyOptions(all), [all]);
  const sel = selection ?? options[0] ?? "EUR";

  const [curDf, currency] = useMemo(
    () => currencyView(all, sel, rates),
    [all, sel, rates],
  );
  const monthly = useMemo(() => monthlyTotals(curDf), [curDf]);

  // --- This-month vs last-month figures ---------------------------------- //
  const thisMonth = dayjs().format("YYYY-MM");
  const lastMonth = dayjs().subtract(1, "month").format("YYYY-MM");
  const val = (month: string, col: "spend" | "income") =>
    monthly.find((m) => m.month === month)?.[col] ?? 0;
  const hasPrev = monthly.some((m) => m.month === lastMonth);

  const spendNow = val(thisMonth, "spend");
  const spendPrev = val(lastMonth, "spend");
  const earnNow = val(thisMonth, "income");
  const earnPrev = val(lastMonth, "income");
  const netNow = earnNow - spendNow;
  const netPrev = earnPrev - spendPrev;
  const srNow = earnNow > 0 ? (netNow / earnNow) * 100 : null;
  const srPrev = earnPrev > 0 ? (netPrev / earnPrev) * 100 : null;

  const moneyDelta = (now: number, prev: number) =>
    hasPrev ? `${fmtSigned(now - prev)} ${currency}` : null;

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
              deltaColor="inverse" // spending more is "bad"
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
          {monthly.length <= 1 ? (
            <Caption>Not enough months of data yet to compare.</Caption>
          ) : (
            <GroupedBarChart byMonth={monthly} currency={currency} />
          )}

          {/* Trend (period switcher + gradient chart) */}
          <SectionTitle>Trend</SectionTitle>
          <OverviewSection
            transactions={all}
            show="both"
            currencySelection={sel}
            rates={rates}
            onSaveRates={saveRates}
          >
            {(df, cur) => {
              const expenses = df.filter((t) => t.amount < 0);
              const income = df.filter((t) => t.amount > 0);
              return (
                <div className="mt-8 grid gap-6 lg:grid-cols-2">
                  <Card>
                    <h3 className="mb-2 text-lg font-semibold">Spending by category</h3>
                    {expenses.length === 0 ? (
                      <Caption>No spending in this period.</Caption>
                    ) : (
                      <HierarchyChart
                        breakdown={categoryBreakdown(expenses, (t) => Math.abs(t.amount))}
                        currency={cur}
                        kind="sunburst"
                      />
                    )}
                  </Card>
                  <Card>
                    <h3 className="mb-2 text-lg font-semibold">Earnings by category</h3>
                    {income.length === 0 ? (
                      <Caption>No earnings in this period.</Caption>
                    ) : (
                      <HierarchyChart
                        breakdown={categoryBreakdown(income, (t) => t.amount)}
                        currency={cur}
                        kind="sunburst"
                      />
                    )}
                  </Card>
                </div>
              );
            }}
          </OverviewSection>
        </>
      )}
    </div>
  );
}
