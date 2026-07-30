import { spawn } from "node:child_process";
import { existsSync, unlinkSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import path from "node:path";

/**
 * Shared low-level primitives for talking to the `agent-browser` CLI.
 * Kept in a separate module so both `browser.ts` (chat automation) and
 * `login.ts` (auth flow) can reuse them without circular imports.
 */

export const AB = "agent-browser";
export const SESSION_NAME = "arena-proxy";
export const STATE_FILE = path.join(process.cwd(), "data", "arena-session.json");
export const ARENA_URL = "https://arena.ai/";

/** Run an agent-browser command, return trimmed stdout. */
export function ab(
  args: string[],
  opts: { timeout?: number } = {},
): Promise<string> {
  const timeout = opts.timeout ?? 60_000;
  return new Promise((resolve, reject) => {
    const proc = spawn(AB, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" },
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(
        new Error(
          `agent-browser timed out after ${timeout}ms: ${args.join(" ")}`,
        ),
      );
    }, timeout);

    proc.stdout.on("data", (chunk) => (stdout += chunk.toString()));
    proc.stderr.on("data", (chunk) => (stderr += chunk.toString()));
    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(new Error(`Failed to spawn agent-browser: ${err.message}`));
    });
    proc.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) resolve(stdout.trim());
      else
        reject(
          new Error(
            `agent-browser exit ${code}: ${stderr.trim() || stdout.trim()}`,
          ),
        );
    });
  });
}

/** Run agent-browser with the global --session flag (persistent context). */
export function abSession(
  args: string[],
  opts: { timeout?: number } = {},
): Promise<string> {
  return ab(["--session", SESSION_NAME, ...args], opts);
}

/** Wait helper. */
export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Ensure the state file directory exists. */
export async function ensureStateDir(): Promise<void> {
  await mkdir(path.dirname(STATE_FILE), { recursive: true });
}

/** Delete the saved session file. */
export function deleteStateFile(): void {
  if (existsSync(STATE_FILE)) {
    try {
      unlinkSync(STATE_FILE);
    } catch {
      /* ignore */
    }
  }
}

/** Whether a saved session file exists. */
export function hasSavedSession(): boolean {
  return existsSync(STATE_FILE);
}

/**
 * Parse one line of the interactive text snapshot into a SnapshotElement.
 * Exported so other modules can parse snapshots the same way.
 */
export interface SnapshotElement {
  ref: string;
  role: string;
  name: string;
  value: string;
  expanded?: boolean;
  disabled?: boolean;
  checked?: boolean;
  level?: number;
  selected?: boolean;
}

export function parseLine(line: string): SnapshotElement | null {
  const m = line.match(/^\s*-\s+(.*)$/);
  if (!m) return null;
  let rest = m[1];

  const roleMatch = rest.match(/^([\w-]+)\s*/);
  if (!roleMatch) return null;
  const role = roleMatch[1];
  rest = rest.slice(roleMatch[0].length);

  let name = "";
  if (rest.startsWith('"')) {
    let i = 1;
    let buf = "";
    while (i < rest.length) {
      const ch = rest[i];
      if (ch === "\\" && i + 1 < rest.length) {
        buf += rest[i + 1];
        i += 2;
        continue;
      }
      if (ch === '"') {
        i++;
        break;
      }
      buf += ch;
      i++;
    }
    name = buf;
    rest = rest.slice(i).trimStart();
  }

  const attrs: Record<string, string | true> = {};
  let ref = "";
  while (rest.startsWith("[")) {
    const end = rest.indexOf("]");
    if (end === -1) break;
    const inside = rest.slice(1, end).trim();
    rest = rest.slice(end + 1).trimStart();
    const parts = inside.split(",").map((p) => p.trim()).filter(Boolean);
    for (const part of parts) {
      const eq = part.indexOf("=");
      if (eq === -1) {
        attrs[part] = true;
      } else {
        const key = part.slice(0, eq).trim();
        const val = part.slice(eq + 1).trim();
        attrs[key] = val;
      }
    }
  }

  if (typeof attrs.ref === "string") {
    ref = attrs.ref;
    delete attrs.ref;
  }

  let value = "";
  if (rest.startsWith(":")) {
    value = rest.slice(1).trim();
  }

  return {
    ref,
    role,
    name,
    value,
    expanded:
      attrs.expanded === "true"
        ? true
        : attrs.expanded === "false"
          ? false
          : undefined,
    disabled: attrs.disabled === true,
    checked:
      attrs.checked === "true"
        ? true
        : attrs.checked === "false"
          ? false
          : undefined,
    level: typeof attrs.level === "string" ? parseInt(attrs.level, 10) : undefined,
    selected: attrs.selected === "true" ? true : undefined,
  };
}

/** Capture the interactive snapshot and return the flat element list. */
export async function snapshot(): Promise<SnapshotElement[]> {
  const out = await abSession(["snapshot", "-i"]);
  const lines = out.split("\n");
  const elements: SnapshotElement[] = [];
  for (const line of lines) {
    const el = parseLine(line);
    if (el && el.ref) elements.push(el);
  }
  return elements;
}

/** Find the first element matching a predicate. */
export function find(
  elements: SnapshotElement[],
  pred: (e: SnapshotElement) => boolean,
): SnapshotElement | undefined {
  return elements.find(pred);
}

/** Find all elements matching a predicate. */
export function findAll(
  elements: SnapshotElement[],
  pred: (e: SnapshotElement) => boolean,
): SnapshotElement[] {
  return elements.filter(pred);
}
