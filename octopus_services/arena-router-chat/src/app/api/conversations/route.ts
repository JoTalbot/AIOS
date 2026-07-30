/**
 * GET  /api/conversations — list all conversations for the caller's scope.
 * PUT  /api/conversations — replace all conversations for the caller's scope
 *                           (body: { conversations: Conversation[] }).
 *
 * Auth: same API-key gate as /api/v1/* (requireApiKey). In open mode the
 * scope collapses to "default".
 */
import { NextResponse } from "next/server";

import { requireApiKey } from "@/lib/arena/auth";
import { getScope, listConversations, replaceConversations } from "@/lib/conversations";
import type { Conversation } from "@/lib/chat/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const authError = requireApiKey(req);
  if (authError) return authError;
  try {
    const scope = getScope(req);
    const conversations = await listConversations(scope);
    return NextResponse.json({ conversations });
  } catch (e) {
    return NextResponse.json(
      { error: "Failed to load conversations", detail: String(e) },
      { status: 500 },
    );
  }
}

export async function PUT(req: Request) {
  const authError = requireApiKey(req);
  if (authError) return authError;
  let body: { conversations?: Conversation[] };
  try {
    body = (await req.json()) as { conversations?: Conversation[] };
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  const conversations = Array.isArray(body?.conversations)
    ? body!.conversations.slice(0, 50)
    : [];
  try {
    const scope = getScope(req);
    await replaceConversations(scope, conversations);
    return NextResponse.json({ ok: true, count: conversations.length });
  } catch (e) {
    return NextResponse.json(
      { error: "Failed to save conversations", detail: String(e) },
      { status: 500 },
    );
  }
}
