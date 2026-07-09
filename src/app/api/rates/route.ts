import { NextRequest, NextResponse } from "next/server";

import { getMeta, setMeta } from "@/lib/db";
import { DEFAULT_RATES, FX_META_KEY, type Rates } from "@/lib/money";

export const dynamic = "force-dynamic";

/** Return EUR conversion rates, merging any user overrides over defaults. */
function currentRates(): Rates {
  const rates: Rates = { ...DEFAULT_RATES };
  const raw = getMeta(FX_META_KEY);
  if (raw) {
    try {
      for (const [k, v] of Object.entries(JSON.parse(raw))) {
        const num = Number(v);
        if (Number.isFinite(num)) rates[k] = num;
      }
    } catch {
      // Malformed overrides are ignored, matching the original app.
    }
  }
  return rates;
}

/** GET /api/rates — manual FX rates (1 unit = N EUR), defaults merged in. */
export async function GET() {
  return NextResponse.json(currentRates());
}

/** PUT /api/rates — persist user-edited conversion rates. Body: {rates}. */
export async function PUT(request: NextRequest) {
  const { rates } = (await request.json()) as { rates: Rates };
  setMeta(FX_META_KEY, JSON.stringify(rates));
  return NextResponse.json(currentRates());
}
