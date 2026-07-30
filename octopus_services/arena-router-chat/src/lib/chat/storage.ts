/**
 * Conversation persistence.
 *
 * Primary store: server (SQLite via /api/conversations) — source of truth.
 * Secondary: localStorage (`arena_router_conversations`) — instant-load
 * cache + offline fallback.
 *
 * The UI loads from server on mount (falls back to localStorage if the server
 * is unreachable) and persists on every change: localStorage immediately,
 * server after a short debounce.
 */

import type { Conversation } from "./types";

const CONV_KEY = "arena_router_conversations";
const ACTIVE_KEY = "arena_router_active_conversation";
const MAX_CONVERSATIONS = 50;

// ─── localStorage (cache + fallback) ──────────────────────────────────────

/** Load all conversations from localStorage (newest first). */
export function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(CONV_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Conversation[];
    if (!Array.isArray(parsed)) return [];
    return parsed.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

/** Persist conversations to localStorage. Trims to MAX_CONVERSATIONS. */
export function saveConversations(conversations: Conversation[]): void {
  if (typeof window === "undefined") return;
  try {
    const trimmed = conversations
      .slice()
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, MAX_CONVERSATIONS);
    window.localStorage.setItem(CONV_KEY, JSON.stringify(trimmed));
  } catch {
    // Quota exceeded or serialization error — silently drop.
  }
}

/** Load the active conversation id from localStorage. */
export function loadActiveConversationId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_KEY);
}

/** Persist the active conversation id. */
export function saveActiveConversationId(id: string | null): void {
  if (typeof window === "undefined") return;
  if (id) {
    window.localStorage.setItem(ACTIVE_KEY, id);
  } else {
    window.localStorage.removeItem(ACTIVE_KEY);
  }
}

/** Generate a short unique id. */
export function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Auto-generate a conversation title from the first user message. */
export function deriveTitle(text: string): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= 50) return clean || "New chat";
  return clean.slice(0, 47) + "…";
}

/**
 * Merge two conversation lists by id, preferring the fresher entry
 * (higher updatedAt) on conflict. Used on mount to migrate old
 * localStorage history into the server store without losing it.
 */
export function mergeConversations(
  a: Conversation[],
  b: Conversation[],
): Conversation[] {
  const byId = new Map<string, Conversation>();
  for (const c of [...a, ...b]) {
    const existing = byId.get(c.id);
    if (!existing || c.updatedAt > existing.updatedAt) {
      byId.set(c.id, c);
    }
  }
  return Array.from(byId.values())
    .sort((x, y) => y.updatedAt - x.updatedAt)
    .slice(0, MAX_CONVERSATIONS);
}

// ─── Server store (source of truth) ───────────────────────────────────────

const API_BASE = "/chat/api/conversations";

/**
 * Fetch all conversations from the server.
 * Returns `null` if the server is unreachable (so the caller can fall back
 * to the localStorage cache); returns `[]` if the server is reachable but
 * there is genuinely no history.
 */
export async function fetchConversationsFromServer(
  apiKey: string,
): Promise<Conversation[] | null> {
  try {
    const r = await fetch(API_BASE, {
      headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
    });
    if (!r.ok) return null;
    const data = (await r.json()) as { conversations?: Conversation[] };
    if (!Array.isArray(data?.conversations)) return null;
    return data.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return null;
  }
}

/** Persist the full conversation list to the server. Caller debounces. */
export async function saveConversationsToServer(
  conversations: Conversation[],
  apiKey: string,
): Promise<boolean> {
  try {
    const r = await fetch(API_BASE, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      body: JSON.stringify({ conversations }),
    });
    return r.ok;
  } catch {
    return false;
  }
}
