"use client";

import { useMemo, useState } from "react";
import dayjs from "dayjs";

import { UNSPECIFIED, categoryBreakdown } from "@/lib/analytics";
import { allCategories, allSubcategories, colorFor, subcategoriesOf } from "@/lib/categories";
import { fmtNum } from "@/lib/format";
import { currencyOptions, currencyView } from "@/lib/money";
import type { Transaction } from "@/lib/types";
import { HBarChart } from "@/components/charts/HBarChart";
import { RatesEditor } from "@/components/RatesEditor";
import { useFinanceData } from "@/components/useFinanceData";
import {
  Button,
  Caption,
  MultiSelectChips,
  Notice,
  PageTitle,
  RadioPills,
  SectionTitle,
  Select,
} from "@/components/ui";

// Time-window switcher for this page. "All time" applies no date filter.
const TX_PERIODS = ["1M", "3M", "1Y", "All time"] as const;
const TX_PERIOD_MONTHS: Record<string, number> = { "1M": 1, "3M": 3, "1Y": 12 };

/** ISO start date for a period label, or `null` for the all-time view. */
function periodStart(label: string): string | null {
  const months = TX_PERIOD_MONTHS[label];
  if (months === undefined) return null;
  return dayjs().subtract(months, "month").format("YYYY-MM-DD");
}

type Edit = { category: string; subcategory: string; notes: string };

const PAGE_SIZE = 300;

export default function TransactionsPage() {
  const { transactions, rates, saveRates, refresh, loading } = useFinanceData();

  const [period, setPeriod] = useState<string>("All time");
  const [search, setSearch] = useState("");
  const [selAccounts, setSelAccounts] = useState<string[]>([]);
  const [selCurrency, setSelCurrency] = useState<string | null>(null);
  const [cat, setCat] = useState<string | null>(null);
  const [sub, setSub] = useState<string | null>(null);
  const [edits, setEdits] = useState<Map<number, Edit>>(new Map());
  const [message, setMessage] = useState<string | null>(null);
  const [visible, setVisible] = useState(PAGE_SIZE);

  const all = useMemo(() => transactions ?? [], [transactions]);
  const accounts = useMemo(() => [...new Set(all.map((t) => t.account))].sort(), [all]);
  const curOptions = useMemo(() => currencyOptions(all), [all]);
  const currencySel = selCurrency ?? curOptions[0] ?? "EUR";

  // --- Base frame for the drill bars (period + search/account filters) ----- //
  const startDate = periodStart(period);
  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return all.filter(
      (t) =>
        (!startDate || t.date >= startDate) &&
        (selAccounts.length === 0 || selAccounts.includes(t.account)) &&
        (!needle ||
          t.description.toLowerCase().includes(needle) ||
          t.notes.toLowerCase().includes(needle)),
    );
  }, [all, startDate, selAccounts, search]);

  const [base, dispCurrency] = useMemo(
    () => currencyView(filtered, currencySel, rates),
    [filtered, currencySel, rates],
  );

  // --- Transactions table rows (narrowed to the current drill path) -------- //
  // The table shows raw rows (original amounts/currencies), like the original.
  const tableRows = useMemo(
    () =>
      filtered.filter(
        (t) =>
          (cat === null || t.category === cat) &&
          (sub === null || (sub === UNSPECIFIED ? t.subcategory === "" : t.subcategory === sub)),
      ),
    [filtered, cat, sub],
  );

  const catOptions = useMemo(
    () =>
      [...new Set([...allCategories(), ...all.map((t) => t.category)])]
        .filter((c) => c !== "")
        .sort(),
    [all],
  );
  const subOptions = useMemo(
    () =>
      [...new Set([...allSubcategories(), ...all.map((t) => t.subcategory)])]
        .filter((s) => s !== "")
        .sort(),
    [all],
  );

  function editOf(t: Transaction): Edit {
    return edits.get(t.id) ?? { category: t.category, subcategory: t.subcategory, notes: t.notes };
  }

  function setEdit(t: Transaction, patch: Partial<Edit>) {
    const next = new Map(edits);
    next.set(t.id, { ...editOf(t), ...patch });
    setEdits(next);
  }

  async function saveChanges() {
    const updates: (Edit & { id: number })[] = [];
    for (const t of all) {
      const edit = edits.get(t.id);
      if (!edit) continue;
      let newSub = edit.subcategory || "";
      const validSubs = subcategoriesOf(edit.category);
      if (newSub && validSubs.length > 0 && !validSubs.includes(newSub)) newSub = "";
      const newNotes = edit.notes || "";
      if (
        edit.category !== t.category ||
        newSub !== (t.subcategory || "") ||
        newNotes !== (t.notes || "")
      ) {
        updates.push({ id: t.id, category: edit.category, subcategory: newSub, notes: newNotes });
      }
    }
    if (updates.length > 0) {
      await fetch("/api/transactions", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
      });
      await refresh();
    }
    setEdits(new Map());
    setMessage(`Saved ${updates.length} change(s).`);
  }

  async function applyRules() {
    const res = await fetch("/api/rules/apply", { method: "POST" });
    const { changed } = await res.json();
    await refresh();
    setMessage(`Updated ${changed} transaction(s) from category rules.`);
  }

  if (loading) return <PageTitle>📂 Transactions</PageTitle>;

  if (all.length === 0) {
    return (
      <div>
        <PageTitle>📂 Transactions</PageTitle>
        <div className="mt-4">
          <Notice>
            No transactions yet. Import a CSV on the <b>Import</b> page first.
          </Notice>
        </div>
      </div>
    );
  }

  const inputClass =
    "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-400";

  return (
    <div>
      <PageTitle>📂 Transactions</PageTitle>

      {/* Time window + filters */}
      <div className="mt-4 flex flex-wrap items-end gap-4">
        <RadioPills options={TX_PERIODS} value={period} onChange={setPeriod} />
        <div className="min-w-64 flex-1">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-600">Search description or notes</span>
            <input
              type="text"
              className={inputClass}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
        </div>
        {accounts.length > 1 && (
          <MultiSelectChips
            label="Account"
            options={accounts}
            selected={selAccounts}
            onChange={setSelAccounts}
          />
        )}
        {curOptions.length > 1 && (
          <div className="w-40">
            <Select
              label="Chart currency"
              value={currencySel}
              options={curOptions}
              onChange={setSelCurrency}
            />
          </div>
        )}
      </div>
      <div className="mt-3">
        <RatesEditor transactions={all} rates={rates} onSave={saveRates} />
      </div>

      {/* Breadcrumb */}
      <div className="mt-6 flex flex-wrap items-center gap-2">
        <Button
          disabled={cat === null}
          onClick={() => {
            setCat(null);
            setSub(null);
          }}
        >
          🏠 All categories
        </Button>
        {cat && (
          <Button disabled={sub === null} onClick={() => setSub(null)}>
            ◂ {cat}
          </Button>
        )}
        <span className="text-sm text-slate-600 dark:text-slate-300">
          All categories
          {cat && (
            <>
              {" › "}
              <b>{cat}</b>
            </>
          )}
          {sub && (
            <>
              {" › "}
              <b>{sub}</b>
            </>
          )}
        </span>
      </div>

      {/* Drill-down charts */}
      <div className="mt-4">
        {base.length === 0 ? (
          <Notice>No transactions match your search/account filters.</Notice>
        ) : cat === null ? (
          <>
            <Caption>
              Click a <b>category</b> bar to drill in.
            </Caption>
            <HBarChart
              items={(() => {
                const byCat = new Map<string, number>();
                for (const t of base) byCat.set(t.category, (byCat.get(t.category) ?? 0) + Math.abs(t.amount));
                return [...byCat.entries()].map(([label, value]) => ({
                  label,
                  value,
                  color: colorFor(label),
                }));
              })()}
              valueLabel={`Total (${dispCurrency})`}
              minHeight={260}
              onBarClick={(label) => {
                setCat(label);
                setSub(null);
              }}
            />
          </>
        ) : sub === null ? (
          <>
            <Caption>
              Click a <b>subcategory</b> of <i>{cat}</i> to see its transactions.
            </Caption>
            <HBarChart
              items={categoryBreakdown(
                base.filter((t) => t.category === cat),
                (t) => Math.abs(t.amount),
              ).map((row) => ({
                label: row.subcategory,
                value: row.value,
                color: colorFor(cat),
              }))}
              valueLabel={`Total (${dispCurrency})`}
              minHeight={220}
              perBarHeight={40}
              onBarClick={setSub}
            />
          </>
        ) : null}
      </div>

      {/* Transactions table */}
      <hr className="mt-8 border-slate-200 dark:border-slate-800" />
      <SectionTitle>Transactions</SectionTitle>
      <Caption>
        Showing {tableRows.length} transaction(s) ·{" "}
        {startDate === null ? "all time" : `last ${period}`}. Edit <b>category</b>,{" "}
        <b>subcategory</b> and <b>notes</b> inline, then save.
      </Caption>

      <div className="mt-3 max-h-[620px] overflow-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Account</th>
              <th className="px-3 py-2">Currency</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Subcategory</th>
              <th className="px-3 py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.slice(0, visible).map((t) => {
              const edit = editOf(t);
              return (
                <tr key={t.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                  <td className="px-3 py-1.5 text-slate-400 dark:text-slate-500">{t.id}</td>
                  <td className="whitespace-nowrap px-3 py-1.5">{t.date}</td>
                  <td className="max-w-xs truncate px-3 py-1.5" title={t.description}>
                    {t.description}
                  </td>
                  <td
                    className={`whitespace-nowrap px-3 py-1.5 text-right font-medium ${
                      t.amount < 0
                        ? "text-red-600 dark:text-red-400"
                        : "text-green-600 dark:text-green-400"
                    }`}
                  >
                    {fmtNum(t.amount, 2)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-1.5">{t.account}</td>
                  <td className="px-3 py-1.5">{t.currency}</td>
                  <td className="px-3 py-1.5">
                    <select
                      className="w-40 rounded border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
                      value={edit.category}
                      onChange={(e) => setEdit(t, { category: e.target.value })}
                    >
                      {catOptions.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-1.5">
                    <select
                      className="w-44 rounded border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
                      value={edit.subcategory}
                      onChange={(e) => setEdit(t, { subcategory: e.target.value })}
                    >
                      <option value="" />
                      {subOptions.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-1.5">
                    <input
                      type="text"
                      className="w-40 rounded border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
                      value={edit.notes}
                      onChange={(e) => setEdit(t, { notes: e.target.value })}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {tableRows.length > visible && (
          <div className="border-t border-slate-100 p-3 text-center dark:border-slate-800">
            <Button onClick={() => setVisible(visible + PAGE_SIZE)}>
              Show {Math.min(PAGE_SIZE, tableRows.length - visible)} more (of{" "}
              {tableRows.length - visible} remaining)
            </Button>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <Button variant="primary" onClick={saveChanges}>
          Save changes
        </Button>
        <Button onClick={applyRules}>Apply rules to uncategorized</Button>
      </div>
      {message && (
        <div className="mt-3">
          <Notice kind="success">{message}</Notice>
        </div>
      )}
    </div>
  );
}
