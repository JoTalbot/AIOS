/**
 * CAPTCHA solver for arena.ai's reCAPTCHA Enterprise.
 *
 * Uses 2Captcha API (https://2captcha.com) to solve reCAPTCHA v2 / Enterprise
 * challenges. The solver is invoked when the chat flow detects a "Security
 * Verification" dialog after sending a message.
 *
 * Cost: ~$2.99 per 1000 reCAPTCHA v2 solves (~$0.003 per solve).
 *
 * Configuration (env vars):
 *   ANTI_CAPTCHA_API_KEY   Required. Your 2Captcha API key.
 *   ANTI_CAPTCHA_SERVICE   Optional. "2captcha" (default), "anticaptcha", "capsolver".
 *
 * Usage:
 *   import { solveRecaptcha } from "@/lib/arena/captcha";
 *   const token = await solveRecaptcha({
 *     sitekey: "SITE_KEY_FROM_PROVIDER",
 *     pageUrl: "https://arena.ai/c/019f584d-...",
 *   });
 *   // → token is the g-recaptcha-response string to inject into the page.
 */

const TWO_CAPTCHA_IN_URL = "https://2captcha.com/in.php";
const TWO_CAPTCHA_RES_URL = "https://2captcha.com/res.php";
const ANTI_CAPTCHA_IN_URL = "https://api.anti-captcha.com/createTask";
const ANTI_CAPTCHA_RES_URL = "https://api.anti-captcha.com/getTaskResult";
const CAPSOLVER_IN_URL = "https://api.capsolver.com/createTask";
const CAPSOLVER_RES_URL = "https://api.capsolver.com/getTaskResult";

export interface SolveOptions {
  sitekey: string;
  pageUrl: string;
  /** Optional: is this reCAPTCHA Enterprise (vs v2)? Default: false. */
  enterprise?: boolean;
  /** Optional: action string for reCAPTCHA v3 / Enterprise. */
  action?: string;
  /** Optional: override the service for this call. */
  service?: "2captcha" | "anticaptcha" | "capsolver";
  /** Optional: max time to wait for solution (default: 180s). */
  timeoutMs?: number;
}

export interface SolveResult {
  ok: boolean;
  token?: string;
  cost?: number; // in USD
  solveTimeMs?: number;
  error?: string;
  taskId?: string;
}

/** Get the configured service name. */
export function getConfiguredService(): "2captcha" | "anticaptcha" | "capsolver" {
  const v = (process.env.ANTI_CAPTCHA_SERVICE || "2captcha").toLowerCase();
  if (v === "anticaptcha") return "anticaptcha";
  if (v === "capsolver") return "capsolver";
  return "2captcha";
}

/** Whether CAPTCHA solving is configured (API key present). */
export function isCaptchaSolverEnabled(): boolean {
  return !!(process.env.ANTI_CAPTCHA_API_KEY && process.env.ANTI_CAPTCHA_API_KEY.length > 10);
}

/** Sleep helper. */
function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Solve a reCAPTCHA challenge via the configured service.
 *
 * Returns the g-recaptcha-response token, which the caller must inject into
 * the page's `#g-recaptcha-response` textarea (and typically call the
 * form's submit or the reCAPTCHA callback).
 */
export async function solveRecaptcha(opts: SolveOptions): Promise<SolveResult> {
  const apiKey = process.env.ANTI_CAPTCHA_API_KEY;
  if (!apiKey) {
    return { ok: false, error: "ANTI_CAPTCHA_API_KEY env var not set" };
  }

  const service = opts.service || getConfiguredService();
  const startedAt = Date.now();
  const timeoutMs = opts.timeoutMs ?? 180_000;

  let taskId: string;
  try {
    taskId = await submitTask(service, apiKey, opts);
  } catch (err) {
    return {
      ok: false,
      error: `Failed to submit task: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  // Poll for the result.
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await sleep(5_000); // Most services need 5-30s to solve.
    try {
      const result = await pollResult(service, apiKey, taskId);
      if (result.status === "ready") {
        return {
          ok: true,
          token: result.token,
          cost: result.cost,
          solveTimeMs: Date.now() - startedAt,
          taskId,
        };
      }
      if (result.status === "failed") {
        return {
          ok: false,
          error: result.error || "Task failed",
          taskId,
          solveTimeMs: Date.now() - startedAt,
        };
      }
      // else: still pending — keep polling.
    } catch (err) {
      // Transient errors are fine — keep polling.
    }
  }

  return {
    ok: false,
    error: `Timed out after ${timeoutMs}ms waiting for CAPTCHA solution`,
    taskId,
    solveTimeMs: Date.now() - startedAt,
  };
}

// ─── 2Captcha ──────────────────────────────────────────────────────────

async function submitTask(
  service: "2captcha" | "anticaptcha" | "capsolver",
  apiKey: string,
  opts: SolveOptions,
): Promise<string> {
  if (service === "2captcha") {
    return submit2Captcha(apiKey, opts);
  }
  if (service === "anticaptcha") {
    return submitAntiCaptcha(apiKey, opts);
  }
  return submitCapSolver(apiKey, opts);
}

async function pollResult(
  service: "2captcha" | "anticaptcha" | "capsolver",
  apiKey: string,
  taskId: string,
): Promise<{ status: "ready" | "pending" | "failed"; token?: string; cost?: number; error?: string }> {
  if (service === "2captcha") {
    return poll2Captcha(apiKey, taskId);
  }
  if (service === "anticaptcha") {
    return pollAntiCaptcha(apiKey, taskId);
  }
  return pollCapSolver(apiKey, taskId);
}

/** Submit to 2Captcha's in.php endpoint. */
async function submit2Captcha(apiKey: string, opts: SolveOptions): Promise<string> {
  const params = new URLSearchParams({
    key: apiKey,
    method: opts.enterprise ? "userrecaptcha" : "userrecaptcha",
    googlekey: opts.sitekey,
    pageurl: opts.pageUrl,
    json: "1",
  });
  if (opts.enterprise) params.set("enterprise", "1");
  if (opts.action) params.set("action", opts.action);

  const r = await fetch(`${TWO_CAPTCHA_IN_URL}?${params}`, { method: "GET" });
  const j = (await r.json()) as { status: number; request: string };
  if (j.status !== 1) {
    throw new Error(`2captcha submit failed: ${j.request}`);
  }
  return j.request; // captcha ID
}

/** Poll 2Captcha's res.php endpoint. */
async function poll2Captcha(
  apiKey: string,
  captchaId: string,
): Promise<{ status: "ready" | "pending" | "failed"; token?: string; cost?: number; error?: string }> {
  const params = new URLSearchParams({
    key: apiKey,
    action: "get",
    id: captchaId,
    json: "1",
  });
  const r = await fetch(`${TWO_CAPTCHA_RES_URL}?${params}`, { method: "GET" });
  const j = (await r.json()) as { status: number; request: string };
  if (j.status === 1) {
    return { status: "ready", token: j.request };
  }
  if (j.request === "CAPCHA_NOT_READY") {
    return { status: "pending" };
  }
  return { status: "failed", error: j.request };
}

// ─── Anti-Captcha ──────────────────────────────────────────────────────

async function submitAntiCaptcha(apiKey: string, opts: SolveOptions): Promise<string> {
  const body = {
    clientKey: apiKey,
    task: opts.enterprise
      ? {
          type: "RecaptchaV2EnterpriseTaskProxyless",
          websiteURL: opts.pageUrl,
          websiteKey: opts.sitekey,
        }
      : {
          type: "NoCaptchaTaskProxyless",
          websiteURL: opts.pageUrl,
          websiteKey: opts.sitekey,
        },
  };
  const r = await fetch(ANTI_CAPTCHA_IN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = (await r.json()) as { errorId: number; taskId?: number; errorCode?: string };
  if (j.errorId !== 0) {
    throw new Error(`anti-captcha submit failed: ${j.errorCode}`);
  }
  return String(j.taskId);
}

async function pollAntiCaptcha(
  apiKey: string,
  taskId: string,
): Promise<{ status: "ready" | "pending" | "failed"; token?: string; cost?: number; error?: string }> {
  const body = { clientKey: apiKey, taskId: parseInt(taskId, 10) };
  const r = await fetch(ANTI_CAPTCHA_RES_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = (await r.json()) as {
    errorId: number;
    status?: string;
    solution?: { gRecaptchaResponse: string };
    errorCode?: string;
    cost?: number;
  };
  if (j.errorId !== 0) {
    if (j.errorCode === "CAPTCHA_NOT_READY" || j.errorCode === "ERROR_CAPTCHA_UNSOLVABLE") {
      return { status: "pending" };
    }
    return { status: "failed", error: j.errorCode };
  }
  if (j.status === "ready" && j.solution?.gRecaptchaResponse) {
    return { status: "ready", token: j.solution.gRecaptchaResponse, cost: j.cost };
  }
  return { status: "pending" };
}

// ─── CapSolver ────────────────────────────────────────────────────────

async function submitCapSolver(apiKey: string, opts: SolveOptions): Promise<string> {
  const body = {
    clientKey: apiKey,
    task: opts.enterprise
      ? {
          type: "ReCaptchaV2EnterpriseTaskProxyless",
          websiteURL: opts.pageUrl,
          websiteKey: opts.sitekey,
        }
      : {
          type: "NoCaptchaTaskProxyless",
          websiteURL: opts.pageUrl,
          websiteKey: opts.sitekey,
        },
  };
  const r = await fetch(CAPSOLVER_IN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = (await r.json()) as { errorId: number; taskId?: string; errorCode?: string };
  if (j.errorId !== 0) {
    throw new Error(`capsolver submit failed: ${j.errorCode}`);
  }
  return j.taskId!;
}

async function pollCapSolver(
  apiKey: string,
  taskId: string,
): Promise<{ status: "ready" | "pending" | "failed"; token?: string; cost?: number; error?: string }> {
  const body = { clientKey: apiKey, taskId };
  const r = await fetch(CAPSOLVER_RES_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = (await r.json()) as {
    errorId: number;
    status?: string;
    solution?: { gRecaptchaResponse: string };
    errorCode?: string;
    cost?: string;
  };
  if (j.errorId !== 0) {
    if (j.errorCode === "CAPTCHA_NOT_READY" || j.errorCode === "ERROR_CAPTCHA_UNSOLVABLE") {
      return { status: "pending" };
    }
    return { status: "failed", error: j.errorCode };
  }
  if (j.status === "ready" && j.solution?.gRecaptchaResponse) {
    return { status: "ready", token: j.solution.gRecaptchaResponse, cost: j.cost ? parseFloat(j.cost) : undefined };
  }
  return { status: "pending" };
}
