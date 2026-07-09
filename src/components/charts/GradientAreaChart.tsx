"use client";

import type { TimeseriesPoint } from "@/lib/analytics";
import { EARN_RGB, SPEND_RGB, fmtNum } from "@/lib/format";
import { EChart, type EChartsOption } from "./EChart";

export type SeriesShow = "both" | "spend" | "earn";

function areaSeries(name: string, data: number[], rgb: string) {
  return {
    name,
    type: "line" as const,
    data,
    showSymbol: false,
    lineStyle: { color: `rgb(${rgb})`, width: 2 },
    itemStyle: { color: `rgb(${rgb})` },
    // Subtle gradient along the y-axis: fades from a light tint near the
    // line down to fully transparent at the baseline.
    areaStyle: {
      color: {
        type: "linear" as const,
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: `rgba(${rgb}, 0.22)` },
          { offset: 0.4, color: `rgba(${rgb}, 0.08)` },
          { offset: 1, color: `rgba(${rgb}, 0)` },
        ],
      },
    },
  };
}

/** Gradient-filled area chart of spendings / earnings over time. */
export function GradientAreaChart({
  data,
  currency,
  show = "both",
}: {
  data: TimeseriesPoint[];
  currency: string;
  show?: SeriesShow;
}) {
  const series = [];
  if (show === "both" || show === "earn") {
    series.push(areaSeries("Earnings", data.map((p) => p.income), EARN_RGB));
  }
  if (show === "both" || show === "spend") {
    series.push(areaSeries("Spendings", data.map((p) => p.spend), SPEND_RGB));
  }

  const option: EChartsOption = {
    grid: { left: 64, right: 16, top: 36, bottom: 28 },
    legend: { top: 0, left: 0 },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => `${fmtNum(Number(v), 2)} ${currency}`,
    },
    xAxis: { type: "category", data: data.map((p) => p.t), boundaryGap: false },
    yAxis: { type: "value", name: `Amount (${currency})`, nameLocation: "middle", nameGap: 48, min: 0 },
    series,
  };
  return <EChart option={option} height={360} />;
}
