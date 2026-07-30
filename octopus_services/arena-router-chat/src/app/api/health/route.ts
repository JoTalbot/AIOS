import { NextResponse } from "next/server";
import { queue } from "@/lib/arena/queue";
import { existsSync } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/health
 * ---------------
 * Lightweight liveness + queue-depth probe. Used by the playground UI
 * to show the current queue state and whether the proxy is reachable.
 */
export async function GET() {
  const stateFile = path.join(process.cwd(), "data", "arena-session.json");

  return NextResponse.json({
    status: "ok",
    queue: {
      busy: queue.isBusy,
      current_task_id: queue.currentTaskId,
      pending: queue.list().filter((e) => e.status === "pending").length,
      recent: queue.list().slice(0, 10),
    },
    session_file_present: existsSync(stateFile),
    timestamp: new Date().toISOString(),
  });
}
