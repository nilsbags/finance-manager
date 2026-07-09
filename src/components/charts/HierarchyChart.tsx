"use client";

import type { BreakdownRow } from "@/lib/analytics";
import { colorFor } from "@/lib/categories";
import { fmtNum } from "@/lib/format";
import { EChart, type EChartsOption } from "./EChart";

/**
 * Sunburst or treemap of category -> subcategory totals. Sectors are coloured
 * by their top-level category using the shared palette.
 */
export function HierarchyChart({
  breakdown,
  currency,
  kind = "sunburst",
}: {
  breakdown: BreakdownRow[];
  currency: string;
  kind?: "sunburst" | "treemap";
}) {
  // Nest rows into category -> subcategory children, keeping insertion order
  // (the breakdown is already sorted by value, largest first).
  const byCategory = new Map<string, { name: string; value: number }[]>();
  for (const row of breakdown) {
    const children = byCategory.get(row.category) ?? [];
    children.push({ name: row.subcategory, value: row.value });
    byCategory.set(row.category, children);
  }
  const data = [...byCategory.entries()].map(([category, children]) => ({
    name: category,
    itemStyle: { color: colorFor(category) },
    children,
  }));

  const tooltip = {
    formatter: (params: unknown) => {
      const p = params as { name: string; value: number };
      return `<b>${p.name}</b><br/>${fmtNum(Number(p.value), 2)} ${currency}`;
    },
  };

  const option: EChartsOption =
    kind === "sunburst"
      ? {
          tooltip,
          series: {
            type: "sunburst",
            data,
            radius: [0, "92%"],
            label: { minAngle: 12, overflow: "truncate", width: 90 },
            emphasis: { focus: "ancestor" },
          },
        }
      : {
          tooltip,
          series: {
            type: "treemap",
            data,
            roam: false,
            nodeClick: false,
            breadcrumb: { show: false },
            label: { show: true },
            upperLabel: { show: true, height: 24 },
            levels: [
              { itemStyle: { borderWidth: 0, gapWidth: 3 } },
              { itemStyle: { gapWidth: 1, borderColorSaturation: 0.5 } },
            ],
          },
        };

  return <EChart option={option} height={420} />;
}
