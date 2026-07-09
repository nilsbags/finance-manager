import { NextResponse } from "next/server";

import { reloadStarterRules } from "@/lib/db";

export const dynamic = "force-dynamic";

/** POST /api/rules/starter — add any built-in starter rules not already present. */
export async function POST() {
  const added = reloadStarterRules();
  return NextResponse.json({ added });
}
