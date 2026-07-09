"use client";

import { useMemo } from "react";

import { categoryBreakdown, monthLabel, monthlyTotals } from "@/lib/analytics";
import { colorFor } from "@/lib/categories";
import { EARN_RGB, SPEND_RGB, fmtNum } from "@/lib/format";
import type { Transaction } from "@/lib/types";
import { HBarChart } from "@/components/charts/HBarChart";
import { HierarchyChart } from "@/components/charts/HierarchyChart";
import { SimpleBarChart } from "@/components/charts/SimpleBarChart";
import { OverviewSection } from "@/components/OverviewSection";
import { useFinanceData } from "@/components/useFinanceData";
import { Caption, Card, Notice, PageTitle, SectionTitle } from "@/components/ui";

/**
 * Spendings and Earnings are the same page over opposite halves of the data:
 * a cumulative gradient chart, three metrics, a category treemap, top
 * subcategories, a by-month bar chart and a top merchants/sources table.
 */
export function FlowPage({ kind }: { kind: "spend" | "earn" }) {
  const { transactions, rates, saveRates, loading } = useFinanceData();
  const all = useMemo(() => transactions ?? [], [transactions]);

  const spend = kind === "spend";
  const title = spend ? "🛒 Spendings" : "💰 Earnings";
  const noun = spend ? "Spending" : "Earnings";
  const verb = spend ? "spent" : "earned";
  const rgb = spend ? SPEND_RGB : EARN_RGB;
  const value = spend ? (t: Transaction) => -t.amount : (t: Transaction) => t.amount;

  if (loading) return <PageTitle>{title}</PageTitle>;

  if (all.length === 0) {
    return (
      <div>
        <PageTitle>{title}</PageTitle>
        <div className="mt-4">
          <Notice>
            No transactions yet. Import a CSV on the <b>Import</b> page first.
          </Notice>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageTitle>{title}</PageTitle>
      <div className="mt-4">
        <OverviewSection
          transactions={all}
          show={kind}
          cumulative
          rates={rates}
          onSaveRates={saveRates}
        >
          {(df, currency) => {
            const rows = df.filter((t) => (spend ? t.amount < 0 : t.amount > 0));
            if (rows.length === 0) {
              return (
                <div className="mt-6">
                  <Notice>No {noun.toLowerCase()} in the selected period.</Notice>
                </div>
              );
            }

            const total = rows.reduce((acc, t) => acc + value(t), 0);
            const breakdown = categoryBreakdown(rows, value);
            const bySub = breakdown.slice(0, 15).map((row) => ({
              label: `${row.category} › ${row.subcategory}`,
              value: row.value,
              color: colorFor(row.category),
            }));
            const byMonth = monthlyTotals(rows);
            const monthValues = byMonth.map((m) => (spend ? m.spend : m.income));

            const topMerchants = new Map<string, number>();
            for (const t of rows) {
              topMerchants.set(t.description, (topMerchants.get(t.description) ?? 0) + value(t));
            }
            const top = [...topMerchants.entries()]
              .sort((a, b) => b[1] - a[1])
              .slice(0, 15);

            return (
              <>
                {/* Metrics */}
                <div className="mt-6 grid gap-4 sm:grid-cols-3">
                  <Card>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      Total {verb} ({currency})
                    </div>
                    <div className="mt-1 text-2xl font-bold">{fmtNum(total, 2)}</div>
                  </Card>
                  <Card>
                    <div className="text-sm text-slate-500 dark:text-slate-400">Transactions</div>
                    <div className="mt-1 text-2xl font-bold">{fmtNum(rows.length)}</div>
                  </Card>
                  <Card>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      Avg / transaction ({currency})
                    </div>
                    <div className="mt-1 text-2xl font-bold">{fmtNum(total / rows.length, 2)}</div>
                  </Card>
                </div>

                {/* By category & subcategory (treemap) */}
                <SectionTitle>
                  {noun} by category &amp; subcategory
                </SectionTitle>
                <HierarchyChart breakdown={breakdown} currency={currency} kind="treemap" />

                {/* By subcategory (bar) */}
                <SectionTitle>Top subcategories</SectionTitle>
                <HBarChart
                  items={bySub}
                  valueLabel={`${spend ? "Spent" : "Earned"} (${currency})`}
                  minHeight={380}
                  perBarHeight={25}
                />

                {/* By month */}
                <SectionTitle>{noun} by month</SectionTitle>
                <SimpleBarChart
                  labels={byMonth.map((m) => monthLabel(m.month))}
                  values={monthValues}
                  color={`rgb(${rgb})`}
                  valueLabel={`${spend ? "Spent" : "Earned"} (${currency})`}
                />

                {/* Top merchants / sources */}
                <SectionTitle>{spend ? "Top merchants" : "Top sources"}</SectionTitle>
                <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400">
                      <tr>
                        <th className="px-4 py-2">{spend ? "Merchant" : "Source"}</th>
                        <th className="px-4 py-2 text-right">
                          {spend ? "Spent" : "Earned"} ({currency})
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {top.map(([description, amount]) => (
                        <tr key={description} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                          <td className="max-w-md truncate px-4 py-1.5" title={description}>
                            {description}
                          </td>
                          <td className="px-4 py-1.5 text-right font-medium">{fmtNum(amount, 2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-2">
                  <Caption>Top 15 by total {verb}.</Caption>
                </div>
              </>
            );
          }}
        </OverviewSection>
      </div>
    </div>
  );
}
