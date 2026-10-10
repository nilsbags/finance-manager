"use client";

import type { MonthlyTotal } from "@/lib/analytics";
import { monthLabel } from "@/lib/analytics";
import { EARN_RGB, SPEND_RGB, fmtNum } from "@/lib/format";
import { EChart, type EChartsOption } from "./EChart";

/** Grouped bar chart comparing spendings vs. earnings across recent months. */
export function GroupedBarChart({
  byMonth,
  currency,
  months = 12,
}: {
  byMonth: MonthlyTotal[];
  currency: string;
  months?: number;
}) {
  const recent = byMonth.slice(-months);

  const option: EChartsOption = {
    grid: { left: 64, right: 16, top: 36, bottom: 28 },
    legend: { top: 0, left: 0 },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => `${fmtNum(Number(v), 2)} ${currency}`,
    },
    xAxis: { type: "category", data: recent.map((m) => monthLabel(m.month)) },
    yAxis: { type: "value", name: `Amount (${currency})`, nameLocation: "middle", nameGap: 48, min: 0 },
    series: [
      {
        name: "Spendings",
        type: "bar",
        data: recent.map((m) => m.spend),
        itemStyle: { color: `rgb(${SPEND_RGB})` },
      },
      {
        name: "Earnings",
        type: "bar",
        data: recent.map((m) => m.income),
        itemStyle: { color: `rgb(${EARN_RGB})` },
      },
    ],
  };
  return <EChart option={option} height={340} />;
}
