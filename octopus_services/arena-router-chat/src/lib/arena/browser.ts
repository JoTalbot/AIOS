import { spawn } from "node:child_process";
import { existsSync, readFileSync, unlinkSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import type {
  BrowserChatResult,
  SessionStatus,
} from "./types";
import { findModel } from "./models";

/**
 * BrowserAutomation (Playwright variant for the Octopus server).
 * ----------------------------------------------------------------
 * Drives arena.ai's Direct Chat using Playwright with the persistent Chrome
 * profile `octopus-gemini-bridge` (which already has a Google session).
 *
 * The chat flow is implemented in a separate Python file `chat_script.py`
 * (kept alongside this file). We shell out to python3 and parse its JSON
 * output. Keeping the Python in a separate file (instead of an inline
 * template literal) avoids Next.js's template-literal escape handling
 * mangling the Python source during bundling.
 */

const DEFAULT_PROFILE = "/root/.config/octopus-gemini-bridge/profile";
const SESSION_FILE = path.join(process.cwd(), "data", "arena-session.json");

/** Lazy-load the Python chat script (avoids SSR build-time file read). */
let _chatScript: string | null = null;
function getChatScript(): string {
  if (_chatScript === null) {
    const candidates = [
      path.join(process.cwd(), "src", "lib", "arena", "chat_script.py"),
      path.join(__dirname, "chat_script.py"),
    ];
    for (const p of candidates) {
      try {
        if (existsSync(p)) {
          _chatScript = readFileSync(p, "utf-8");
          return _chatScript;
        }
      } catch {
        /* try next */
      }
    }
    _chatScript = "";
  }
  return _chatScript;
}

let _sessionCheckScript: string | null = null;
function getSessionCheckScript(): string {
  if (_sessionCheckScript === null) {
    const candidates = [
      path.join(process.cwd(), "src", "lib", "arena", "session_check.py"),
      path.join(__dirname, "session_check.py"),
    ];
    for (const p of candidates) {
      try {
        if (existsSync(p)) {
          _sessionCheckScript = readFileSync(p, "utf-8");
          return _sessionCheckScript;
        }
      } catch {
        /* try next */
      }
    }
    _sessionCheckScript = "";
  }
  return _sessionCheckScript;
}

function getProfilePath(): string {
  return process.env.ARENA_GOOGLE_PROFILE || DEFAULT_PROFILE;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

interface PythonResult {
  ok: boolean;
  text?: string;
  error?: string;
  blocked?: boolean;
  block_reason?: "login_required" | "captcha" | "unknown";
  trace_id?: string;
  debug?: string[];
}

/** Spawn python3 with the script + argv, return parsed JSON result. */
function runPythonChat(
  script: string,
  argv: string[],
  timeoutMs: number,
): Promise<PythonResult> {
  return new Promise((resolve, reject) => {
    console.error(`[arena] spawning python3 with script len=${script.length}, argv=${JSON.stringify(argv.map(a => a.slice(0, 40)))}`);
    const proc = spawn("python3", ["-c", script, ...argv], {
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" },
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(new Error(`python3 timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    proc.stdout.on("data", (c) => (stdout += c.toString()));
    proc.stderr.on("data", (c) => (stderr += c.toString()));
    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(new Error(`Failed to spawn python3: ${err.message}`));
    });
    proc.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) {
        try {
          const parsed = JSON.parse(stdout.trim()) as PythonResult;
          resolve(parsed);
        } catch {
          resolve({
            ok: false,
            error: `Failed to parse python output: ${stdout.slice(0, 500)}`,
          });
        }
      } else {
        console.error(`[arena] python3 exit ${code}`);
        console.error(`[arena] stderr: ${stderr.slice(0, 1000)}`);
        reject(new Error(`python3 exit ${code}: ${stderr.trim() || stdout.trim()}`));
      }
    });
  });
}

/** Run a python script that returns JSON, for session checks. */
function runPythonJson(
  script: string,
  argv: string[],
  timeoutMs: number,
): Promise<PythonResult> {
  return runPythonChat(script, argv, timeoutMs);
}

/**
 * Send one prompt to one model and return the reply.
 * The actual browser automation happens in the Python script.
 */
export async function runChat(opts: {
  model: string;
  prompt: string;
  timeoutMs?: number;
  /** Files to attach to the outgoing prompt (images/PDF only). */
  attachments?: ArenaAttachmentFile[];
}): Promise<BrowserChatResult> {
  const startedAt = Date.now();
  const timeout = opts.timeoutMs ?? 180_000;
  const profile = getProfilePath();
  const model = findModel(opts.model);
  if (!model) {
    return {
      text: "",
      model_used: opts.model,
      elapsed_ms: 0,
      blocked: true,
      block_reason: "unknown",
    };
  }

  const pyScript = getChatScript();
  const attachments: ArenaAttachmentFile[] = opts.attachments ?? [];
  const attachArg = attachments.map(a => a.path).join("|");
  console.error("[arena] runChat argv:", [profile, model.arena_label, opts.prompt.slice(0, 50), String(timeout), `files=${attachments.length}`]);
  let result: PythonResult;
  try {
    result = await runPythonChat(
      pyScript,
      [profile, model.arena_label, opts.prompt, String(timeout), attachArg],
      timeout + 60_000,
    );
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : String(err);
    console.error("[arena] runChat spawn error:", errMsg);
    return {
      text: "",
      model_used: opts.model,
      elapsed_ms: Date.now() - startedAt,
      blocked: true,
      block_reason: "unknown",
    };
  }

  // If the Python script itself reported an error, log it for debugging.
  if (result.error) {
    console.error("[arena] Python script error:", result.error);
    console.error("[arena] Python debug:", JSON.stringify(result.debug));
  }

  return {
    text: result.text ?? "",
    model_used: opts.model,
    elapsed_ms: Date.now() - startedAt,
    blocked: result.blocked ?? false,
    block_reason: result.block_reason,
    trace_id: result.trace_id,
  };
}

/** Check the arena.ai session status (logged in or not). */
export async function getSessionStatus(): Promise<SessionStatus> {
  const profile = getProfilePath();
  const status: SessionStatus = {
    has_saved_session: existsSync(SESSION_FILE),
    logged_in: false,
  };

  if (!existsSync(profile)) {
    status.last_error = `Chrome profile not found: ${profile}`;
    return status;
  }

  try {
    const result = await runPythonJson(
      getSessionCheckScript(),
      [profile],
      60_000,
    );
    status.logged_in = result.ok && (result.text === "logged_in");
    status.user_identifier = undefined; // session check doesn't extract it
    status.last_verified_at = new Date().toISOString();
    if (result.error) status.last_error = result.error;
  } catch (err) {
    status.last_error = err instanceof Error ? err.message : String(err);
  }

  return status;
}

/** Save the session — for the Playwright variant, the Google bridge login
 * script already saves it. This is a no-op that ensures the file exists. */
export async function saveSession(): Promise<void> {
  if (!existsSync(SESSION_FILE)) {
    mkdirSync(path.dirname(SESSION_FILE), { recursive: true });
    writeFileSync(SESSION_FILE, JSON.stringify({ cookies: [], origins: [] }));
  }
}

/** Delete the saved session file. */
export async function clearSession(): Promise<void> {
  if (existsSync(SESSION_FILE)) {
    try {
      unlinkSync(SESSION_FILE);
    } catch {
      /* ignore */
    }
  }
}

/** No persistent browser to close. */
export async function closeBrowser(): Promise<void> {}

/** Not implemented for the Playwright variant. */
export async function screenshot(_path: string): Promise<void> {}

// ─── Python scripts ─────────────────────────────────────────────────────

/**
 * Python chat script. Reads profile, model_label, prompt, timeout_ms from argv.
 * Returns JSON on stdout: {ok, text, blocked, block_reason, trace_id, error, debug}.
 *
 * The script:
 *   1. Launches Chromium with the persistent profile (already logged in).
 *   2. Opens arena.ai.
 *   3. Switches Battle Mode → Direct Chat (if needed).
 *   4. Selects the requested model.
 *   5. Types the prompt and clicks Send.
 *   6. Handles Terms-of-Use / login-wall / captcha dialogs.
 *   7. Polls until the response stabilises.
 *   8. Extracts the assistant reply.
 */
// CHAT_PYTHON_SCRIPT is loaded lazily via getChatScript()

// SESSION_CHECK_SCRIPT is loaded lazily via getSessionCheckScript()
