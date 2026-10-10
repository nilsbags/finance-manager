import { NextRequest, NextResponse } from "next/server";

import {
  insertTransactions,
  loadRules,
  updateAccountBalances,
} from "@/lib/db";
import {
  DEDUCED_INCOME_DESC,
  DEDUCED_OUTFLOW_DESC,
  latestBalances,
  prepareRows,
  type RawRow,
} from "@/lib/importer";
import { categorize } from "@/lib/rules";
import type { ColumnMapping, ImportOptions } from "@/lib/types";

export const dynamic = "force-dynamic";

interface ImportRequest {
  rows: RawRow[];
  mapping: ColumnMapping;
  options: ImportOptions;
}

/** POST /api/import — normalise raw CSV rows, insert them, update balances. */
export async function POST(request: NextRequest) {
  const { rows, mapping, options } = (await request.json()) as ImportRequest;

  const rules = options.applyRules ? loadRules() : null;
  const { valid, skipped } = prepareRows(rows, mapping, {
    defaultAccount: options.defaultAccount,
    defaultCurrency: options.defaultCurrency,
    decimalComma: options.decimalComma,
    dayfirst: options.dayfirst,
    categorize: rules ? (desc) => categorize(desc, rules) : undefined,
    deduceIncome: options.deduceIncome,
  });

  const deduced = valid.filter(
    (r) => r.description === DEDUCED_INCOME_DESC || r.description === DEDUCED_OUTFLOW_DESC,
  ).length;
  const inserted = insertTransactions(valid);
  const duplicates = valid.length - inserted;

  // Persist the latest running balance per account so the dashboard can show it.
  let balances: ReturnType<typeof latestBalances> = [];
  if (mapping.balance) {
    balances = latestBalances(rows, mapping, {
      defaultAccount: options.defaultAccount,
      defaultCurrency: options.defaultCurrency,
      decimalComma: options.decimalComma,
      dayfirst: options.dayfirst,
    });
    if (balances.length > 0) updateAccountBalances(balances);
  }

  return NextResponse.json({
    inserted,
    duplicates,
    deduced,
    skipped,
    balancesUpdated: balances.length,
  });
}
