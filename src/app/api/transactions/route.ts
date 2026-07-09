import { NextRequest, NextResponse } from "next/server";

import {
  deleteAllTransactions,
  fetchTransactions,
  updateTransaction,
} from "@/lib/db";

export const dynamic = "force-dynamic";

/** GET /api/transactions — all transactions, newest first. */
export async function GET() {
  return NextResponse.json(fetchTransactions());
}

interface TxUpdate {
  id: number;
  category: string;
  subcategory: string;
  notes: string;
}

/** PATCH /api/transactions — bulk-update editable fields. Body: {updates: TxUpdate[]}. */
export async function PATCH(request: NextRequest) {
  const { updates } = (await request.json()) as { updates: TxUpdate[] };
  for (const u of updates) {
    updateTransaction(u.id, {
      category: u.category,
      subcategory: u.subcategory ?? "",
      notes: u.notes ?? "",
    });
  }
  return NextResponse.json({ updated: updates.length });
}

/** DELETE /api/transactions — remove every transaction (danger zone). */
export async function DELETE() {
  const removed = deleteAllTransactions();
  return NextResponse.json({ removed });
}
