import { NextResponse } from "next/server";

import { getAccountBalances } from "@/lib/db";

export const dynamic = "force-dynamic";

/** GET /api/balances — most recent known balance per account (from imports). */
export async function GET() {
  return NextResponse.json(getAccountBalances());
}
