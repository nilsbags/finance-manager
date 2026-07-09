import { NextResponse } from "next/server";

import { applyRulesToExisting } from "@/lib/db";

export const dynamic = "force-dynamic";

/** POST /api/rules/apply — re-categorize uncategorized transactions. */
export async function POST() {
  const changed = applyRulesToExisting(true);
  return NextResponse.json({ changed });
}
