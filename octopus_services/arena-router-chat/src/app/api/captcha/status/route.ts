import { NextResponse } from "next/server";
import { isCaptchaSolverEnabled, getConfiguredService } from "@/lib/arena/captcha";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/captcha/status
 * -----------------------
 * Returns whether CAPTCHA solving is configured (ANTI_CAPTCHA_API_KEY env var
 * is set) and which service is active.
 *
 * The playground UI uses this to display whether reCAPTCHA challenges will be
 * auto-solved or returned as a 503 error.
 */
export async function GET() {
  return NextResponse.json({
    enabled: isCaptchaSolverEnabled(),
    service: getConfiguredService(),
  });
}
