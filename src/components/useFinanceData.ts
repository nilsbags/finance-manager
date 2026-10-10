"use client";

import { useCallback, useEffect, useState } from "react";

import type { Rates } from "@/lib/money";
import type { Transaction } from "@/lib/types";

/**
 * Loads the full transaction set + manual FX rates once per page, the same
 * way every Streamlit page started with `fetch_transactions()`. Pages then
 * filter/aggregate client-side for instant interactivity.
 */
export function useFinanceData() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [rates, setRates] = useState<Rates>({});

  const refresh = useCallback(async () => {
    const [txRes, ratesRes] = await Promise.all([
      fetch("/api/transactions"),
      fetch("/api/rates"),
    ]);
    setTransactions(await txRes.json());
    setRates(await ratesRes.json());
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveRates = useCallback(async (next: Rates) => {
    setRates(next); // optimistic — the editor stays responsive while typing
    await fetch("/api/rates", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rates: next }),
    });
  }, []);

  return { transactions, rates, saveRates, refresh, loading: transactions === null };
}
