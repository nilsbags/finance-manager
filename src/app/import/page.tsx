"use client";

import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

import {
  detectDayfirst,
  detectDecimalComma,
  guessColumn,
  guessOptionalColumn,
} from "@/lib/csv";
import type { ColumnMapping } from "@/lib/types";
import {
  Button,
  Caption,
  Checkbox,
  Expander,
  Notice,
  PageTitle,
  Select,
  SectionTitle,
  TextInput,
} from "@/components/ui";

const NONE_LABEL = "— not in file —";
const DELIMITERS = [",", ";", "\\t", "|"];
const ENCODINGS = ["utf-8", "latin-1", "cp1252"];

type RawRow = Record<string, string>;

interface ImportResult {
  inserted: number;
  duplicates: number;
  deduced: number;
  skipped: (RawRow & { _reason: string })[];
  balancesUpdated: number;
}

export default function ImportPage() {
  const [txCount, setTxCount] = useState<number | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [clearMsg, setClearMsg] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [delimiter, setDelimiter] = useState(",");
  const [encoding, setEncoding] = useState("utf-8");
  const [parseError, setParseError] = useState<string | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [rows, setRows] = useState<RawRow[]>([]);

  // Column mapping + options.
  const [dateCol, setDateCol] = useState("");
  const [descCol, setDescCol] = useState("");
  const [amountCol, setAmountCol] = useState("");
  const [accountCol, setAccountCol] = useState(NONE_LABEL);
  const [currencyCol, setCurrencyCol] = useState(NONE_LABEL);
  const [balanceCol, setBalanceCol] = useState(NONE_LABEL);
  const [defaultAccount, setDefaultAccount] = useState("Main");
  const [defaultCurrency, setDefaultCurrency] = useState("EUR");
  const [decimalComma, setDecimalComma] = useState(false);
  const [dayfirst, setDayfirst] = useState(true);
  const [applyRules, setApplyRules] = useState(true);
  const [deduceIncome, setDeduceIncome] = useState(false);

  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  const refreshCount = () =>
    fetch("/api/transactions")
      .then((r) => r.json())
      .then((all: unknown[]) => setTxCount(all.length));

  useEffect(() => {
    void refreshCount();
  }, []);

  // (Re-)parse whenever the file or the parsing options change.
  useEffect(() => {
    if (!file) return;
    let cancelled = false;
    setParseError(null);
    setResult(null);
    file
      .arrayBuffer()
      .then((buf) => {
        const label = encoding === "cp1252" ? "windows-1252" : encoding;
        const text = new TextDecoder(label).decode(buf);
        const parsed = Papa.parse<RawRow>(text, {
          header: true,
          delimiter: delimiter === "\\t" ? "\t" : delimiter,
          skipEmptyLines: true,
        });
        if (cancelled) return;
        const fields = (parsed.meta.fields ?? []).filter((f) => f !== "");
        if (fields.length === 0 || parsed.data.length === 0) {
          setColumns([]);
          setRows([]);
          setParseError("The uploaded file has no rows.");
          return;
        }
        setColumns(fields);
        setRows(parsed.data);
      })
      .catch((exc: unknown) => {
        if (!cancelled) setParseError(`Could not read the CSV: ${String(exc)}`);
      });
    return () => {
      cancelled = true;
    };
  }, [file, delimiter, encoding]);

  // Auto-guess the column mapping whenever the columns change.
  useEffect(() => {
    if (columns.length === 0) return;
    setDateCol(
      columns[guessColumn(columns, ["date", "buchungsdatum", "datum", "booking date", "value date", "booking"])],
    );
    setDescCol(
      columns[
        guessColumn(columns, [
          "description", "desc", "payee", "merchant", "narrative",
          "verwendungszweck", "verwendung", "details", "text",
        ])
      ],
    );
    setAmountCol(columns[guessColumn(columns, ["amount", "betrag", "umsatz", "value", "sum"])]);
    setAccountCol(
      guessOptionalColumn(columns, ["account name", "account", "konto", "card number", "card", "iban"]) ??
        NONE_LABEL,
    );
    setCurrencyCol(
      guessOptionalColumn(columns, ["currency", "account currency", "währung", "waehrung", "ccy"]) ??
        NONE_LABEL,
    );
    setBalanceCol(
      guessOptionalColumn(columns, [
        "balance", "running balance", "saldo", "kontostand", "saldo nach buchung", "new balance",
      ]) ?? NONE_LABEL,
    );
  }, [columns]);

  // Defaults auto-detected from the selected date / amount columns.
  useEffect(() => {
    if (rows.length === 0 || !amountCol) return;
    setDecimalComma(detectDecimalComma(rows.map((r) => r[amountCol])));
  }, [rows, amountCol]);
  useEffect(() => {
    if (rows.length === 0 || !dateCol) return;
    setDayfirst(detectDayfirst(rows.map((r) => r[dateCol])));
  }, [rows, dateCol]);

  const hasBalance = balanceCol !== NONE_LABEL;
  useEffect(() => {
    setDeduceIncome(hasBalance);
  }, [hasBalance]);

  const preview = useMemo(() => rows.slice(0, 10), [rows]);

  async function clearAll() {
    const res = await fetch("/api/transactions", { method: "DELETE" });
    const { removed } = await res.json();
    setClearMsg(`Removed ${removed} transaction(s). You can re-import below.`);
    setConfirmClear(false);
    void refreshCount();
  }

  async function runImport() {
    setImporting(true);
    setResult(null);
    try {
      const mapping: ColumnMapping = {
        date: dateCol,
        description: descCol,
        amount: amountCol,
        account: accountCol === NONE_LABEL ? null : accountCol,
        currency: currencyCol === NONE_LABEL ? null : currencyCol,
        balance: balanceCol === NONE_LABEL ? null : balanceCol,
      };
      const res = await fetch("/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rows,
          mapping,
          options: {
            defaultAccount,
            defaultCurrency,
            decimalComma,
            dayfirst,
            applyRules,
            deduceIncome: deduceIncome && hasBalance,
          },
        }),
      });
      setResult(await res.json());
      void refreshCount();
    } finally {
      setImporting(false);
    }
  }

  return (
    <div>
      <PageTitle>📥 Import transactions</PageTitle>
      <Caption>Upload a bank CSV, tell the app what each column means, and import.</Caption>

      {/* Danger zone: reset stored transactions */}
      <div className="mt-6">
        <Expander title={`⚠️ Danger zone — ${txCount ?? "…"} transaction(s) stored`}>
          <Caption>
            Use this if an earlier import mapped the wrong columns. It removes all stored
            transactions (your category rules are kept) so you can re-import cleanly.
          </Caption>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <Checkbox
              label="Yes, delete all stored transactions"
              checked={confirmClear}
              onChange={setConfirmClear}
            />
            <Button variant="danger" disabled={!confirmClear} onClick={clearAll}>
              Clear all transactions
            </Button>
          </div>
          {clearMsg && (
            <div className="mt-3">
              <Notice kind="success">{clearMsg}</Notice>
            </div>
          )}
        </Expander>
      </div>

      {/* Upload */}
      <div className="mt-6">
        <input
          type="file"
          accept=".csv"
          className="block w-full max-w-md cursor-pointer rounded-lg border border-slate-300 bg-white text-sm text-slate-600 file:mr-3 file:cursor-pointer file:rounded-l-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2.5 file:text-sm file:font-medium dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:file:bg-slate-700 dark:file:text-slate-200"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {!file ? (
        <div className="mt-4">
          <Notice>Upload a CSV file to begin. Nothing is sent anywhere — parsing happens locally.</Notice>
        </div>
      ) : (
        <>
          <div className="mt-4">
            <Expander title="Parsing options">
              <div className="grid grid-cols-2 gap-4">
                <Select
                  label="Column delimiter"
                  value={delimiter}
                  options={DELIMITERS}
                  onChange={setDelimiter}
                />
                <Select label="File encoding" value={encoding} options={ENCODINGS} onChange={setEncoding} />
              </div>
              <div className="mt-2">
                <Caption>Many European banks export with &lsquo;;&rsquo;.</Caption>
              </div>
            </Expander>
          </div>

          {parseError ? (
            <div className="mt-4">
              <Notice kind="warning">{parseError}</Notice>
            </div>
          ) : (
            columns.length > 0 && (
              <>
                <SectionTitle>Preview</SectionTitle>
                <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400">
                      <tr>
                        {columns.map((c) => (
                          <th key={c} className="whitespace-nowrap px-3 py-2">{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.map((row, i) => (
                        <tr key={i} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                          {columns.map((c) => (
                            <td key={c} className="whitespace-nowrap px-3 py-1.5">{row[c]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <SectionTitle>Map columns</SectionTitle>
                <div className="grid gap-4 sm:grid-cols-3">
                  <Select label="Date column" value={dateCol} options={columns} onChange={setDateCol} />
                  <Select label="Description column" value={descCol} options={columns} onChange={setDescCol} />
                  <Select label="Amount column" value={amountCol} options={columns} onChange={setAmountCol} />
                  <Select
                    label="Account column (optional)"
                    value={accountCol}
                    options={[NONE_LABEL, ...columns]}
                    onChange={setAccountCol}
                  />
                  <Select
                    label="Currency column (optional)"
                    value={currencyCol}
                    options={[NONE_LABEL, ...columns]}
                    onChange={setCurrencyCol}
                  />
                  <Select
                    label="Balance column (optional)"
                    value={balanceCol}
                    options={[NONE_LABEL, ...columns]}
                    onChange={setBalanceCol}
                  />
                </div>
                <div className="mt-1">
                  <Caption>
                    The running account balance lets the app recover income that only shows up as a
                    balance jump, not as its own transaction.
                  </Caption>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <TextInput label="Default account" value={defaultAccount} onChange={setDefaultAccount} />
                  <TextInput label="Default currency" value={defaultCurrency} onChange={setDefaultCurrency} />
                </div>

                <div className="mt-4 space-y-3">
                  <Checkbox
                    label="Amounts use comma as decimal (e.g. 1.234,56)"
                    checked={decimalComma}
                    onChange={setDecimalComma}
                    help="Auto-detected from your amount column — override if needed."
                  />
                  <Checkbox
                    label="Dates are day-first (e.g. 31/12/2025)"
                    checked={dayfirst}
                    onChange={setDayfirst}
                    help="Auto-detected from your date column (ISO dates are not day-first)."
                  />
                  <Checkbox
                    label="Auto-categorize using rules during import"
                    checked={applyRules}
                    onChange={setApplyRules}
                  />
                  <Checkbox
                    label="Deduce income/changes from balance gaps"
                    checked={deduceIncome && hasBalance}
                    onChange={setDeduceIncome}
                    disabled={!hasBalance}
                    help="When the running balance moves by more than the listed transactions in a month, the difference is added as a synthetic entry per account and month — positive months as income, negative months as an outflow. Needs a balance column."
                  />
                </div>

                <div className="mt-6">
                  <Button variant="primary" onClick={runImport} disabled={importing}>
                    {importing ? "Importing…" : "Import transactions"}
                  </Button>
                </div>

                {result && (
                  <div className="mt-4 space-y-3">
                    <Notice kind="success">
                      Imported {result.inserted} new transaction(s). Skipped {result.duplicates}{" "}
                      duplicate(s) and {result.skipped.length} unparseable row(s).
                      {result.deduced > 0 &&
                        ` Includes ${result.deduced} entr(y/ies) deduced from balance changes.`}
                      {result.balancesUpdated > 0 &&
                        ` Updated current balance for ${result.balancesUpdated} account(s).`}
                    </Notice>
                    {result.skipped.length > 0 && (
                      <Expander title={`Show ${result.skipped.length} skipped row(s)`}>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-sm">
                            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500 dark:border-slate-700 dark:text-slate-400">
                              <tr>
                                <th className="px-3 py-2">Reason</th>
                                {columns.map((c) => (
                                  <th key={c} className="whitespace-nowrap px-3 py-2">{c}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {result.skipped.map((row, i) => (
                                <tr key={i} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                                  <td className="whitespace-nowrap px-3 py-1.5 text-red-600 dark:text-red-400">{row._reason}</td>
                                  {columns.map((c) => (
                                    <td key={c} className="whitespace-nowrap px-3 py-1.5">{row[c]}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </Expander>
                    )}
                  </div>
                )}
              </>
            )
          )}
        </>
      )}
    </div>
  );
}
