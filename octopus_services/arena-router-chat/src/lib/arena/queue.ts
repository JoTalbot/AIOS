import { randomUUID } from "node:crypto";
import type { BrowserChatResult, QueueEntry } from "./types";

/**
 * SerialQueue
 * -----------
 * arena.ai's web UI can only handle one conversation at a time in a single
 * browser session, so we must serialise chat requests. This queue:
 *
 *   - Accepts enqueued tasks returning a Promise<BrowserChatResult>.
 *   - Runs them one at a time, in FIFO order.
 *   - Exposes the live queue state via list() for the admin UI.
 *   - Resolves the caller's promise with the result, or rejects on error.
 *
 * The queue is process-wide (a singleton on the module scope), so all
 * API requests share it.
 */

type Task = () => Promise<BrowserChatResult>;

interface InternalEntry extends QueueEntry {
  task: Task;
  resolve: (r: BrowserChatResult) => void;
  reject: (e: unknown) => void;
}

class SerialQueue {
  private entries: Map<string, InternalEntry> = new Map();
  private order: string[] = [];
  private running: boolean = false;
  private currentId: string | null = null;

  /**
   * Enqueue a task. Returns a promise that resolves with the task's result
   * once the task has been executed (which may be later, if the queue is busy).
   */
  enqueue(meta: {
    model: string;
    prompt: string;
    task: Task;
  }): Promise<BrowserChatResult> {
    const id = randomUUID();
    const preview =
      meta.prompt.length > 80 ? meta.prompt.slice(0, 77) + "…" : meta.prompt;

    return new Promise<BrowserChatResult>((resolve, reject) => {
      const entry: InternalEntry = {
        id,
        enqueued_at: Date.now(),
        status: "pending",
        model: meta.model,
        prompt_preview: preview,
        task: meta.task,
        resolve,
        reject,
      };
      this.entries.set(id, entry);
      this.order.push(id);
      void this.pump();
    });
  }

  /** Process the next queued task if nothing is running. */
  private async pump(): Promise<void> {
    if (this.running) return;
    const nextId = this.order.shift();
    if (!nextId) return;

    const entry = this.entries.get(nextId);
    if (!entry) return this.pump();

    this.running = true;
    this.currentId = nextId;
    entry.status = "running";
    entry.started_at = Date.now();

    try {
      const result = await entry.task();
      entry.status = "done";
      entry.completed_at = Date.now();
      entry.result = result;
      entry.resolve(result);
    } catch (err) {
      entry.status = "error";
      entry.completed_at = Date.now();
      entry.error = err instanceof Error ? err.message : String(err);
      entry.reject(err);
    } finally {
      this.running = false;
      this.currentId = null;
      // Trim history to the last 50 entries to avoid unbounded growth.
      if (this.entries.size > 50) {
        const oldest = Array.from(this.entries.keys()).slice(
          0,
          this.entries.size - 50,
        );
        for (const id of oldest) this.entries.delete(id);
      }
      void this.pump();
    }
  }

  /** Snapshot of the queue (newest first), for the admin UI. */
  list(): QueueEntry[] {
    return Array.from(this.entries.values())
      .sort((a, b) => b.enqueued_at - a.enqueued_at)
      .map((e) => {
        // Strip internal fields (task, resolve, reject) before exposing.
        const {
          task: _task,
          resolve: _resolve,
          reject: _reject,
          ...clean
        } = e;
        void _task;
        void _resolve;
        void _reject;
        return clean;
      });
  }

  /** Whether the queue is currently processing a task. */
  get isBusy(): boolean {
    return this.running;
  }

  /** The id of the currently-running task, if any. */
  get currentTaskId(): string | null {
    return this.currentId;
  }
}

/** Process-wide singleton. */
export const queue = new SerialQueue();

/**
 * Convenience wrapper: enqueue a chat task and resolve with its result.
 * The task closure is what actually performs the browser automation.
 */
export function enqueueChat(
  model: string,
  prompt: string,
  task: Task,
): Promise<BrowserChatResult> {
  return queue.enqueue({ model, prompt, task });
}
