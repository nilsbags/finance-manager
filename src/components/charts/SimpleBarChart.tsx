"use client";

import { fmtNum } from "@/lib/format";
import { EChart, type EChartsOption } from "./EChart";

/** Single-series vertical bar chart (the by-month breakdowns). */
export function SimpleBarChart({
  labels,
  values,
  color,
  valueLabel,
  height = 320,
}: {
  labels: string[];
  values: number[];
  color: string;
  valueLabel: string;
  height?: number;
}) {
  const option: EChartsOption = {
    grid: { left: 64, right: 16, top: 16, bottom: 28 },
    tooltip: {
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number };
        return `${p.name}: ${fmtNum(Number(p.value), 2)}`;
      },
    },
    xAxis: { type: "category", data: labels },
    yAxis: { type: "value", name: valueLabel, nameLocation: "middle", nameGap: 48, min: 0 },
    series: { type: "bar", data: values, itemStyle: { color } },
  };
  return <EChart option={option} height={height} />;
}
