import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import path from "node:path";
import type {
  ChatCompletionRequest,
  ChatMessage,
  Attachment,
} from "@/lib/arena/types";
import { findModel } from "@/lib/arena/models";
import { runChat } from "@/lib/arena/browser";
import { enqueueChat } from "@/lib/arena/queue";
import { requireApiKey } from "@/lib/arena/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

/**
 * POST /api/v1/chat/completions
 * -----------------------------
 * OpenAI-compatible chat completion endpoint.
 *
 * If `stream: true` is set in the request body, the response is returned as
 * a Server-Sent Events (SSE) stream of OpenAI-format chunks. Because
 * arena.ai does not expose a true token-level stream, we wait for the full
 * reply and then emit it word-by-word with small delays — clients see a
 * realistic streaming experience.
 *
 * Internally:
 *   1. Flatten messages[] into a single prompt (system + user turns).
 *   2. Enqueue the request on the serial browser queue (one at a time).
 *   3. Drive arena.ai's Direct Chat: pick model, type prompt, send, wait.
 *   4. Return the assistant's reply — streamed or as a single response.
 */
export async function POST(req: Request) {
  // API-key auth check.
  const authError = requireApiKey(req as Request);
  if (authError) return authError;

  let body: ChatCompletionRequest;
  try {
    body = (await req.json()) as ChatCompletionRequest;
  } catch {
    return NextResponse.json(
      { error: { message: "Invalid JSON body", type: "invalid_request_error" } },
      { status: 400 },
    );
  }

  // Validate model.
  const model = findModel(body.model);
  if (!model) {
    return NextResponse.json(
      {
        error: {
          message: `Model "${body.model}" is not available on this proxy. GET /api/v1/models for the full list.`,
          type: "invalid_request_error",
          code: "model_not_found",
        },
      },
      { status: 404 },
    );
  }

  // Validate messages.
  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return NextResponse.json(
      {
        error: {
          message: "messages[] is required and must be non-empty",
          type: "invalid_request_error",
        },
      },
      { status: 400 },
    );
  }

  const { prompt, attachments } = extractLastUserMessage(body.messages);
  const timeoutMs = body.arena?.timeout_ms ?? 180_000;

  // Branch: streaming vs non-streaming.
  if (body.stream) {
    return handleStreaming(model.id, prompt, timeoutMs, attachments);
  }
  return handleNonStreaming(model.id, prompt, timeoutMs, attachments);
}

/** Non-streaming handler — returns a single chat.completion object. */
async function handleNonStreaming(
  modelId: string,
  prompt: string,
  timeoutMs: number,
  attachments: Array<{ path: string; name: string; mime: string }>,
): Promise<Response> {
  try {
    const result = await enqueueChat(modelId, prompt, () =>
      runChat({ model: modelId, prompt, timeoutMs, attachments }),
    );

    if (result.blocked) {
      const reason =
        result.block_reason === "login_required"
          ? "Arena.ai requires login. Use the playground's Session panel to log in, then retry."
          : result.block_reason === "captcha"
            ? "Arena.ai triggered a security verification (reCAPTCHA). Wait a few minutes and retry, or refresh the session via the playground."
            : "Arena.ai blocked the request for an unknown reason.";
      return NextResponse.json(
        {
          error: {
            message: reason,
            type: "arena_blocked",
            code: result.block_reason,
            trace_id: result.trace_id,
          },
        },
        { status: 503 },
      );
    }

    const completionId = `chatcmpl-${randomUUID().replace(/-/g, "").slice(0, 24)}`;
    const created = Math.floor(Date.now() / 1000);

    return NextResponse.json({
      id: completionId,
      object: "chat.completion",
      created,
      model: modelId,
      choices: [
        {
          index: 0,
          message: {
            role: "assistant",
            content: result.text,
          },
          finish_reason: "stop",
        },
      ],
      usage: {
        prompt_tokens: approximateTokens(prompt),
        completion_tokens: approximateTokens(result.text),
        total_tokens: approximateTokens(prompt) + approximateTokens(result.text),
      },
      system_fingerprint: `arena_proxy/${result.elapsed_ms}ms`,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        error: {
          message: `Browser automation failed: ${message}`,
          type: "internal_error",
        },
      },
      { status: 500 },
    );
  }
}

/**
 * Streaming handler — emits an SSE stream of OpenAI-format chunks.
 *
 * Since arena.ai does not expose a real token stream, we:
 *   1. Wait for the full response (via the serial queue).
 *   2. Split the text into chunks (by word, preserving whitespace).
 *   3. Emit one chunk per word with a small delay (~30ms).
 *   4. Close with [DONE].
 *
 * If the request is blocked (login/captcha), we emit a single error chunk
 * and close.
 */
async function handleStreaming(
  modelId: string,
  prompt: string,
  timeoutMs: number,
  attachments: Array<{ path: string; name: string; mime: string}>,
): Promise<Response> {
  const completionId = `chatcmpl-${randomUUID().replace(/-/g, "").slice(0, 24)}`;
  const created = Math.floor(Date.now() / 1000);

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (obj: unknown) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));
      };

      try {
        const result = await enqueueChat(modelId, prompt, () =>
          runChat({ model: modelId, prompt, timeoutMs, attachments }),
        );

        if (result.blocked) {
          const reason =
            result.block_reason === "login_required"
              ? "Arena.ai requires login."
              : result.block_reason === "captcha"
                ? "Arena.ai triggered a security verification."
                : "Arena.ai blocked the request.";
          send({
            id: completionId,
            object: "chat.completion.chunk",
            created,
            model: modelId,
            choices: [
              {
                index: 0,
                delta: { content: `[error: ${reason}]` },
                finish_reason: "error",
              },
            ],
          });
          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          controller.close();
          return;
        }

        // Emit the role chunk first.
        send({
          id: completionId,
          object: "chat.completion.chunk",
          created,
          model: modelId,
          choices: [
            {
              index: 0,
              delta: { role: "assistant", content: "" },
              finish_reason: null,
            },
          ],
        });

        // Split into tokens (words + whitespace) and stream them.
        const tokens = tokenize(result.text);
        for (const tok of tokens) {
          send({
            id: completionId,
            object: "chat.completion.chunk",
            created,
            model: modelId,
            choices: [
              {
                index: 0,
                delta: { content: tok },
                finish_reason: null,
              },
            ],
          });
          // Small delay to mimic token-by-token streaming.
          await new Promise((r) => setTimeout(r, 25));
        }

        // Final chunk with finish_reason.
        send({
          id: completionId,
          object: "chat.completion.chunk",
          created,
          model: modelId,
          choices: [
            {
              index: 0,
              delta: {},
              finish_reason: "stop",
            },
          ],
        });

        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        send({
          id: completionId,
          object: "chat.completion.chunk",
          created,
          model: modelId,
          choices: [
            {
              index: 0,
              delta: { content: `[error: ${message}]` },
              finish_reason: "error",
            },
          ],
        });
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}

/**
 * Split text into stream-friendly tokens: words + the whitespace that
 * follows them. Preserves the original text exactly when concatenated.
 */
function tokenize(text: string): string[] {
  const tokens: string[] = [];
  // Match a word (non-whitespace run) plus any trailing whitespace.
  const re = /\S+\s*/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    tokens.push(m[0]);
  }
  // If the text ends with non-whitespace that didn't match (shouldn't happen
  // with the regex above, but just in case), append the remainder.
  if (tokens.length === 0 && text.length > 0) tokens.push(text);
  return tokens;
}

/**
 * Flatten an OpenAI-style messages[] array into a single prompt string.
 */
/**
 * Extract the last user message from the messages[] array.
 *
 * arena.ai's Direct Chat textbox accepts one prompt at a time, so we send
 * only the latest user turn. Multi-turn context is preserved on arena.ai's
 * side (it remembers the conversation in the same chat session).
 */
interface AttachmentRef { path: string; name: string; mime: string; }

function resolveLocalPath(urlOrPath: string): string | null {
  // URLs like /chat/uploads/<file> are served from public/uploads -> process.cwd()/public/uploads/...
  try {
    const m = /^\/chat\/uploads\/([a-zA-Z0-9._-]+)$/.exec(urlOrPath);
    if (m) return path.join(process.cwd(), "public", "uploads", m[1]);
    if (/^https?:\/\//.test(urlOrPath)) {
      // Remote URL: download to a temp file.
      try {
        const fs = require("node:fs") as typeof import("node:fs");
        const os = require("node:os") as typeof import("node:os");
        const http = require("node:https") as typeof import("node:https");
        const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "arena-up-"));
        const tmpPath = path.join(tmpDir, "attachment.bin");
        const target = new URL(urlOrPath);
        return new Promise<string>((resolve) => {
          const file = fs.createWriteStream(tmpPath);
          http.get(target, (res) => { res.pipe(file); file.on("finish", () => { file.close(() => resolve(tmpPath)); }); })
            .on("error", () => resolve(null));
        }) as any;
      } catch { return null; }
    }
    // Absolute filesystem path — trust it if exists.
    try {
      const fs = require("node:fs") as typeof import("node:fs");
      if (fs.existsSync(urlOrPath)) return urlOrPath;
    } catch {}
    return null;
  } catch { return null; }
}

function extractLastUserMessage(messages: ChatMessage[]): { prompt: string; attachments: AttachmentRef[] } {
  const atts: AttachmentRef[] = [];
  let prompt = "";
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role !== "user") continue;
    const c: any = messages[i].content;
    if (typeof c === "string") {
      prompt = c;
    } else if (Array.isArray(c)) {
      const parts: string[] = [];
      for (const p of c) {
        if (p.type === "text") parts.push(p.text);
        else if (p.type === "image_url") {
          const lp = resolveLocalPath(p.image_url.url);
          if (lp) atts.push({ path: lp, name: "image", mime: "image/*" });
        } else if (p.type === "file") {
          const lp = resolveLocalPath(p.file.url);
          if (lp) atts.push({ path: lp, name: p.file.name || "file", mime: p.file.mime || "application/octet-stream" });
        }
      }
      prompt = parts.join("\n");
    }
    // Legacy attachments on message
    const legacy = (messages[i] as any).attachments as Array<{url:string,name:string,mime:string}> | undefined;
    if (legacy && Array.isArray(legacy)) {
      for (const a of legacy) {
        const lp = resolveLocalPath(a.url);
        if (lp) atts.push({ path: lp, name: a.name, mime: a.mime });
      }
    }
    break;
  }
  if (!prompt) {
    const last: any = messages[messages.length - 1];
    prompt = typeof last.content === "string" ? last.content : "";
  }
  return { prompt, attachments: atts };
}

function flattenMessages(messages: ChatMessage[]): string {
  const parts: string[] = [];

  for (const msg of messages) {
    const content = typeof msg.content === "string" ? msg.content : "";

    switch (msg.role) {
      case "system":
        parts.push(`[System]\n${content}`);
        break;
      case "user":
        parts.push(`[User]\n${content}`);
        break;
      case "assistant":
        parts.push(`[Assistant]\n${content}`);
        break;
      case "tool":
        parts.push(`[Tool ${msg.tool_call_id ?? ""}]\n${content}`);
        break;
    }
  }

  parts.push("[Assistant]\n");
  return parts.join("\n\n");
}

/** Rough token estimate (4 chars per token). */
function approximateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}
