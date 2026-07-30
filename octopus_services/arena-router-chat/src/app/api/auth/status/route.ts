import { NextResponse } from "next/server";
import { isAuthEnabled } from "@/lib/arena/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/auth/status
 * --------------------
 * Returns whether API-key auth is enabled. The playground uses this to
 * decide whether to show the API-key input field.
 */
export async function GET() {
  return NextResponse.json({
    auth_required: isAuthEnabled(),
  });
}
