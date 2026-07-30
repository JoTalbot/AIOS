/**
 * DELETE /api/conversations/:id — delete a single conversation by id.
 */
import { NextResponse } from "next/server";

import { requireApiKey } from "@/lib/arena/auth";
import { getScope, deleteConversation } from "@/lib/conversations";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const authError = requireApiKey(req);
  if (authError) return authError;
  const { id } = await params;
  if (!id) {
    return NextResponse.json({ error: "Missing id" }, { status: 400 });
  }
  try {
    const scope = getScope(req);
    await deleteConversation(scope, id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json(
      { error: "Failed to delete conversation", detail: String(e) },
      { status: 500 },
    );
  }
}
