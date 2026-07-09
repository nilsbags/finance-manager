import { NextRequest, NextResponse } from "next/server";

import { addRule, fetchRules } from "@/lib/db";

export const dynamic = "force-dynamic";

/** GET /api/rules — all rules in priority (insertion) order. */
export async function GET() {
  return NextResponse.json(fetchRules());
}

/** POST /api/rules — add a rule. Body: {pattern, category, subcategory}. */
export async function POST(request: NextRequest) {
  const { pattern, category, subcategory } = (await request.json()) as {
    pattern: string;
    category: string;
    subcategory?: string;
  };
  if (!pattern?.trim()) {
    return NextResponse.json({ error: "A pattern is required." }, { status: 400 });
  }
  addRule(pattern, category, subcategory ?? "");
  return NextResponse.json({ ok: true });
}
