import type { NextRequest } from "next/server";

/**
 * API-key authentication for the proxy.
 *
 * If the environment variable `ARENA_PROXY_API_KEY` is set, every request
 * to /api/v1/* and /api/session must carry an `Authorization: Bearer <key>`
 * (or `X-API-Key: <key>`) header matching it. If the env var is unset,
 * the proxy runs in open mode (no auth) — useful for local development.
 *
 * The playground UI reads the key from localStorage and sends it on every
 * request, so the user only needs to enter it once.
 */

/** Read the configured API key from the environment. */
export function getConfiguredApiKey(): string | null {
  const v = process.env.ARENA_PROXY_API_KEY;
  return v && v.length > 0 ? v : null;
}

/** Whether API-key auth is currently enabled. */
export function isAuthEnabled(): boolean {
  return getConfiguredApiKey() !== null;
}

/** Extract the API key from a request's headers. */
export function extractApiKey(req: NextRequest | Request): string | null {
  // Authorization: Bearer <key>
  const auth = req.headers.get("authorization") ?? req.headers.get("Authorization");
  if (auth) {
    const m = auth.match(/^Bearer\s+(.+)$/i);
    if (m) return m[1].trim();
    // Some clients send the raw key without "Bearer".
    return auth.trim();
  }
  // X-API-Key: <key>
  const xKey = req.headers.get("x-api-key") ?? req.headers.get("X-API-Key");
  if (xKey) return xKey.trim();
  return null;
}

/**
 * Verify the request's API key. Returns `null` if the request is allowed,
 * or an error Response if it should be rejected.
 */
export function requireApiKey(req: NextRequest | Request): Response | null {
  const configured = getConfiguredApiKey();
  if (!configured) {
    return null; // Auth disabled — allow all requests.
  }
  const provided = extractApiKey(req);
  if (!provided || provided !== configured) {
    return new Response(
      JSON.stringify({
        error: {
          message:
            "Invalid or missing API key. Set the Authorization: Bearer <key> header (or X-API-Key).",
          type: "invalid_request_error",
          code: "invalid_api_key",
        },
      }),
      {
        status: 401,
        headers: { "Content-Type": "application/json" },
      },
    );
  }
  return null;
}
