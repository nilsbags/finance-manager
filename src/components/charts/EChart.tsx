"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

// ECharts renders into the DOM, so it must only load in the browser.
const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div />,
});

export type { EChartsOption };

export function EChart({
  option,
  height,
  onClick,
}: {
  option: EChartsOption;
  height: number;
  onClick?: (name: string) => void;
}) {
  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
      onEvents={onClick ? { click: (params: { name?: string }) => params.name && onClick(params.name) } : undefined}
    />
  );
}
