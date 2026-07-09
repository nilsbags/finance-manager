"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { TAXONOMY, allCategories, colorFor, subcategoriesOf } from "@/lib/categories";
import type { RuleRow } from "@/lib/types";
import {
  Button,
  Caption,
  Card,
  MetricCard,
  Notice,
  PageTitle,
  SectionTitle,
  Select,
  Tabs,
  TextInput,
} from "@/components/ui";

function ColorDot({ color, size = 10 }: { color: string; size?: number }) {
  return (
    <span
      className="mr-1.5 inline-block rounded-full"
      style={{ width: size, height: size, background: color }}
    />
  );
}

export default function RulesPage() {
  const [rules, setRules] = useState<RuleRow[] | null>(null);
  const [pattern, setPattern] = useState("");
  const [category, setCategory] = useState(allCategories(false)[0]);
  const [subcategory, setSubcategory] = useState("");
  const [message, setMessage] = useState<{ kind: "success" | "warning"; text: string } | null>(null);

  const refresh = useCallback(
    () =>
      fetch("/api/rules")
        .then((r) => r.json())
        .then(setRules),
    [],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function addRule() {
    if (!pattern.trim()) {
      setMessage({ kind: "warning", text: "A pattern is required." });
      return;
    }
    await fetch("/api/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pattern, category, subcategory }),
    });
    const label = subcategory ? `${category} › ${subcategory}` : category;
    setMessage({ kind: "success", text: `Added rule: "${pattern.trim()}" → ${label}` });
    setPattern("");
    setSubcategory("");
    void refresh();
  }

  async function loadStarterRules() {
    const res = await fetch("/api/rules/starter", { method: "POST" });
    const { added } = await res.json();
    setMessage({ kind: "success", text: `Added ${added} starter rule(s).` });
    void refresh();
  }

  async function applyRulesNow() {
    const res = await fetch("/api/rules/apply", { method: "POST" });
    const { changed } = await res.json();
    setMessage({ kind: "success", text: `Updated ${changed} transaction(s).` });
  }

  async function removeRule(id: number) {
    await fetch(`/api/rules/${id}`, { method: "DELETE" });
    void refresh();
  }

  const grouped = useMemo(() => {
    const map = new Map<string, RuleRow[]>();
    for (const rule of rules ?? []) {
      const group = map.get(rule.category);
      if (group) group.push(rule);
      else map.set(rule.category, [rule]);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [rules]);

  const rulesTab = (
    <div>
      {/* Add a rule */}
      <SectionTitle>Add a rule</SectionTitle>
      <div className="grid items-end gap-4 sm:grid-cols-3">
        <TextInput
          label="If description contains"
          value={pattern}
          onChange={setPattern}
          placeholder="e.g. BILLA"
        />
        <Select
          label="Category"
          value={category}
          options={allCategories(false)}
          onChange={(c) => {
            setCategory(c);
            setSubcategory("");
          }}
        />
        <Select
          label="Subcategory"
          value={subcategory}
          options={["", ...subcategoriesOf(category)]}
          onChange={setSubcategory}
        />
      </div>
      <div className="mt-4">
        <Button variant="primary" onClick={addRule}>
          Add rule
        </Button>
      </div>
      {message && (
        <div className="mt-3">
          <Notice kind={message.kind}>{message.text}</Notice>
        </div>
      )}

      {/* Bulk actions */}
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <MetricCard label="Active rules" value={String(rules?.length ?? "…")} boxed={false} />
        <Button onClick={loadStarterRules}>Load starter rules</Button>
        <Button variant="primary" onClick={applyRulesNow}>
          Apply rules now
        </Button>
      </div>
      <Caption>
        &ldquo;Load starter rules&rdquo; adds any built-in rules you don&apos;t already have;
        &ldquo;Apply rules now&rdquo; re-categorizes uncategorized transactions.
      </Caption>

      <hr className="my-6 border-slate-200" />

      {/* Existing rules, grouped by category */}
      <SectionTitle>Existing rules</SectionTitle>
      {rules !== null && rules.length === 0 ? (
        <Notice>No rules yet. Add one above or load the starter rules.</Notice>
      ) : (
        <div className="space-y-6">
          {grouped.map(([cat, group]) => (
            <div key={cat}>
              <div className="mb-2 font-semibold">
                <ColorDot color={colorFor(cat)} />
                {cat} <span className="font-normal text-slate-400">({group.length})</span>
              </div>
              <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
                {group.map((rule) => (
                  <div key={rule.id} className="flex items-center gap-4 px-4 py-2 text-sm">
                    <div className="flex-1">
                      contains <b>&ldquo;{rule.pattern}&rdquo;</b>
                    </div>
                    <div className="flex-1 text-slate-600">→ {rule.subcategory || "—"}</div>
                    <button
                      type="button"
                      onClick={() => removeRule(rule.id)}
                      className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-500 hover:border-red-300 hover:text-red-600"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const taxonomyTab = (
    <div>
      <SectionTitle>Category taxonomy</SectionTitle>
      <Caption>The full set of categories and their subcategories used across the app.</Caption>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(TAXONOMY).map(([cat, subs]) => (
          <Card key={cat}>
            <div className="mb-2 font-semibold">
              <ColorDot color={colorFor(cat)} size={12} />
              {cat}
            </div>
            <ul className="list-inside list-disc space-y-0.5 text-sm text-slate-600">
              {subs.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <PageTitle>⚙️ Categories &amp; Rules</PageTitle>
      <Caption>
        Rules match a case-insensitive substring in the description and assign a category +
        subcategory. They apply in order — the first match wins.
      </Caption>
      <div className="mt-6">
        <Tabs
          tabs={[
            { label: "Rules", content: rulesTab },
            { label: "Category overview", content: taxonomyTab },
          ]}
        />
      </div>
    </div>
  );
}
