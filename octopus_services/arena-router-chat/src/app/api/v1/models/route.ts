import { NextResponse } from "next/server";
import { ARENA_MODELS, listProviders } from "@/lib/arena/models";
import { requireApiKey, isAuthEnabled } from "@/lib/arena/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/v1/models
 * ------------------
 * OpenAI-compatible model listing. Returns every model the proxy can route
 * to, grouped by provider for client convenience.
 */
export async function GET(req: Request) {
  // API-key auth check (skipped if ARENA_PROXY_API_KEY is unset).
  const authError = requireApiKey(req);
  if (authError) return authError;

  const providers = listProviders();

  return NextResponse.json({
    object: "list",
    data: ARENA_MODELS.map((m) => ({
      id: m.id,
      object: "model",
      created: 1_720_000_000,
      owned_by: m.provider,
      permission: [],
      root: m.id,
      parent: null,
      arena: {
        label: m.arena_label,
        provider: m.provider,
        description: m.description,
        thinking: m.thinking ?? false,
        vision: m.vision ?? false,
      },
    })),
    providers,
    auth_required: isAuthEnabled(),
  });
}
