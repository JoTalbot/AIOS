import { NextResponse } from "next/server";
import {
  getSessionStatus,
  saveSession,
  clearSession,
} from "@/lib/arena/browser";
import { sendMagicLink, completeMagicLink } from "@/lib/arena/login";
import { requireApiKey, isAuthEnabled } from "@/lib/arena/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

/**
 * /api/session — manage the arena.ai browser session.
 *
 *   GET    /api/session                       → current session status
 *   POST   /api/session?action=save           → persist the current browser state
 *   POST   /api/session?action=clear          → delete the saved session
 *   POST   /api/session?action=login          → start email magic-link flow
 *                                              body: { email }
 *   POST   /api/session?action=login_callback → complete magic-link login
 *                                              body: { url }
 *
 * The session file lives at data/arena-session.json and contains the
 * cookies + localStorage agent-browser captured from the live page.
 * It is loaded automatically before every arena.ai navigation, so the
 * user only needs to log in once.
 */

function authCheck(req: Request): Response | null {
  // The /api/session endpoints are protected by the same API key as the
  // chat endpoints, so a public user cannot trigger a login flow on the
  // owner's browser session.
  return requireApiKey(req);
}

export async function GET(req: Request) {
  const authError = authCheck(req);
  if (authError) return authError;

  try {
    const status = await getSessionStatus();
    return NextResponse.json(status);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        has_saved_session: false,
        logged_in: false,
        last_error: message,
      },
      { status: 500 },
    );
  }
}

export async function POST(req: Request) {
  const authError = authCheck(req);
  if (authError) return authError;

  const url = new URL(req.url);
  const action = url.searchParams.get("action") ?? "save";

  try {
    if (action === "save") {
      await saveSession();
      const status = await getSessionStatus();
      return NextResponse.json({ ok: true, status });
    }
    if (action === "clear") {
      await clearSession();
      return NextResponse.json({ ok: true });
    }
    if (action === "login") {
      // Start magic-link flow: send verification email.
      const body = (await req.json().catch(() => ({}))) as { email?: string };
      if (!body.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)) {
        return NextResponse.json(
          { error: "A valid 'email' field is required in the JSON body." },
          { status: 400 },
        );
      }
      const result = await sendMagicLink(body.email);
      return NextResponse.json(result);
    }
    if (action === "login_callback") {
      // Complete magic-link flow: navigate to the URL the user clicked.
      const body = (await req.json().catch(() => ({}))) as { url?: string };
      if (!body.url || !/^https?:\/\//.test(body.url)) {
        return NextResponse.json(
          { error: "A valid 'url' field is required in the JSON body." },
          { status: 400 },
        );
      }
      const status = await completeMagicLink(body.url);
      return NextResponse.json({ ok: true, status });
    }
    if (action === "google_login") {
      // Trigger Google bridge auto-login via the Octopus server-side script.
      // This only works if the proxy is running on the Octopus server (where
      // the Chrome profile with the active Google session lives).
      try {
        const { spawn } = await import("node:child_process");
        const scriptPath = process.env.ARENA_GOOGLE_LOGIN_SCRIPT ||
          "/root/agents/-Octopus/skills/mcp/arena-router/code/google_bridge_login.py";
        const result = await new Promise<{ ok: boolean; output: string }>(
          (resolve) => {
            const proc = spawn("python3", [scriptPath, "--json"], {
              stdio: ["ignore", "pipe", "pipe"],
              env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" },
            });
            let stdout = "";
            let stderr = "";
            const timer = setTimeout(() => {
              proc.kill("SIGKILL");
              resolve({ ok: false, output: "timeout after 180s" });
            }, 180_000);
            proc.stdout.on("data", (c) => (stdout += c.toString()));
            proc.stderr.on("data", (c) => (stderr += c.toString()));
            proc.on("close", (code) => {
              clearTimeout(timer);
              if (code === 0) {
                resolve({ ok: true, output: stdout.trim() });
              } else {
                resolve({ ok: false, output: stderr.trim() || stdout.trim() || `exit ${code}` });
              }
            });
            proc.on("error", (err) => {
              clearTimeout(timer);
              resolve({ ok: false, output: `spawn error: ${err.message}` });
            });
          },
        );

        if (!result.ok) {
          return NextResponse.json(
            {
              ok: false,
              error: `Google bridge login failed. Is the proxy running on the Octopus server? Output: ${result.output}`,
            },
            { status: 502 },
          );
        }

        // Parse the JSON output from google_bridge_login.py.
        let parsed: { ok?: boolean; logged_in?: boolean; user_identifier?: string | null; error?: string | null } = {};
        try {
          parsed = JSON.parse(result.output);
        } catch {
          // The script may have printed non-JSON to stderr; just return raw.
        }

        return NextResponse.json({
          ok: parsed.ok ?? false,
          logged_in: parsed.logged_in ?? false,
          user_identifier: parsed.user_identifier ?? null,
          error: parsed.error ?? null,
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return NextResponse.json(
          { ok: false, error: `Failed to invoke google_bridge_login.py: ${message}` },
          { status: 500 },
        );
      }
    }
    return NextResponse.json(
      { error: `Unknown action: ${action}` },
      { status: 400 },
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

// Suppress unused-import warning for isAuthEnabled — re-exported for the UI.
export { isAuthEnabled };
