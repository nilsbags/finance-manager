"use client";

import { fmtNum } from "@/lib/format";
import { EChart, type EChartsOption } from "./EChart";

export interface HBarItem {
  label: string;
  value: number;
  color: string;
}

/**
 * Horizontal bar chart with per-bar colours, largest bar on top. Used for the
 * category drill-down, top-subcategory and subscription-cost breakdowns.
 * When `onBarClick` is given, bars (and their axis labels) become clickable.
 */
export function HBarChart({
  items,
  valueLabel,
  perBarHeight = 36,
  minHeight = 260,
  decimals = 2,
  onBarClick,
}: {
  items: HBarItem[];
  valueLabel: string;
  perBarHeight?: number;
  minHeight?: number;
  decimals?: number;
  onBarClick?: (label: string) => void;
}) {
  // First axis entry renders at the bottom, so ascending order puts the
  // largest value on top (plotly's "total ascending").
  const sorted = [...items].sort((a, b) => a.value - b.value);

  const option: EChartsOption = {
    grid: { left: 8, right: 24, top: 8, bottom: 28, containLabel: true },
    tooltip: {
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number };
        return `${p.name}: ${fmtNum(Number(p.value), decimals)}`;
      },
    },
    xAxis: { type: "value", name: valueLabel, nameLocation: "middle", nameGap: 24 },
    yAxis: {
      type: "category",
      data: sorted.map((i) => i.label),
      triggerEvent: Boolean(onBarClick),
      axisLabel: { width: 220, overflow: "truncate" },
    },
    series: {
      type: "bar",
      data: sorted.map((i) => ({ value: i.value, itemStyle: { color: i.color } })),
      cursor: onBarClick ? "pointer" : "default",
    },
  };

  return (
    <EChart
      option={option}
      height={Math.max(minHeight, perBarHeight * sorted.length)}
      onClick={onBarClick}
    />
  );
}
