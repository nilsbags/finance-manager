"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

import { useTheme } from "../ThemeProvider";

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
  const { theme } = useTheme();
  return (
    <ReactECharts
      // The built-in dark theme restyles axes/legend/tooltip; its opaque
      // background is overridden so the page background shows through.
      theme={theme === "dark" ? "dark" : undefined}
      option={{ ...option, backgroundColor: "transparent" }}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
      onEvents={onClick ? { click: (params: { name?: string }) => params.name && onClick(params.name) } : undefined}
    />
  );
}
