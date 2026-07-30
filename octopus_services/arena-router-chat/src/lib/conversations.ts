/**
 * Server-side conversation persistence helpers.
 * Scoped per resolved API key (sha256-truncated). Bigint timestamps for epoch-ms.
 */
import { createHash } from "node:crypto";

import { db } from "@/lib/db";
import { extractApiKey, getConfiguredApiKey } from "@/lib/arena/auth";
import type { ChatMessage, Conversation } from "@/lib/chat/types";

/** Resolve a stable scope key for a request. */
export function getScope(req: Request): string {
  const configured = getConfiguredApiKey();
  const provided = (extractApiKey(req) || configured || "default").trim() || "default";
  return createHash("sha256").update(provided).digest("hex").slice(0, 16);
}

interface ConvRow {
  id: string;
  title: string;
  model: string;
  systemPrompt: string | null;
  agentPresetId: string | null;
  messages: string;
  createdAt: bigint;
  updatedAt: bigint;
}

export function rowToConversation(row: ConvRow): Conversation {
  let messages: ChatMessage[] = [];
  try {
    const parsed = JSON.parse(row.messages);
    if (Array.isArray(parsed)) messages = parsed as ChatMessage[];
  } catch {
    /* malformed — leave empty */
  }
  return {
    id: row.id,
    title: row.title,
    model: row.model,
    systemPrompt: row.systemPrompt ?? undefined,
    agentPresetId: row.agentPresetId ?? undefined,
    messages,
    createdAt: Number(row.createdAt),
    updatedAt: Number(row.updatedAt),
  };
}

export function conversationToRow(scope: string, c: Conversation) {
  return {
    id: c.id,
    scope,
    title: c.title ?? "New chat",
    model: c.model ?? "gpt-5.2",
    systemPrompt: c.systemPrompt ?? null,
    agentPresetId: c.agentPresetId ?? null,
    messages: JSON.stringify(c.messages ?? []),
    createdAt: BigInt(c.createdAt ?? 0),
    updatedAt: BigInt(c.updatedAt ?? 0),
  };
}

/** List all conversations for a scope, newest first (max 50). */
export async function listConversations(scope: string): Promise<Conversation[]> {
  const rows = await db.conversation.findMany({
    where: { scope },
    orderBy: { updatedAt: "desc" },
    take: 50,
  });
  return rows.map((r) => rowToConversation(r as unknown as ConvRow));
}

/** Replace the entire conversation set for a scope. */
export async function replaceConversations(
  scope: string,
  convs: Conversation[],
): Promise<void> {
  const data = convs.slice(0, 50).map((c) => conversationToRow(scope, c));
  await db.$transaction([
    db.conversation.deleteMany({ where: { scope } }),
    ...(data.length > 0
      ? [db.conversation.createMany({ data })]
      : []),
  ]);
}

/** Delete a single conversation by id within a scope. */
export async function deleteConversation(
  scope: string,
  id: string,
): Promise<void> {
  await db.conversation.deleteMany({ where: { scope, id } });
}
