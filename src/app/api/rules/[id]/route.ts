import { NextRequest, NextResponse } from "next/server";

import { deleteRule } from "@/lib/db";

export const dynamic = "force-dynamic";

/** DELETE /api/rules/:id */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  deleteRule(Number(id));
  return NextResponse.json({ ok: true });
}
