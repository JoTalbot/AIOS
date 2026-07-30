/**
 * Core type definitions for the Arena AI Browser Proxy.
 *
 * The proxy exposes an OpenAI-compatible API and internally drives
 * arena.ai (formerly lmarena.ai) through a headless browser.
 */

/** An image attachment (OpenAI vision format). */
export interface ImageContentPart {
  type: "image_url";
  image_url: { url: string; detail?: "auto" | "low" | "high" };
}
/** A text content part. */
export interface TextContentPart {
  type: "text";
  text: string;
}
/** A file reference (PDF or other attached file). */
export interface FileContentPart {
  type: "file";
  file: { url: string; name: string; mime: string; size?: number };
}
export type ContentPart = TextContentPart | ImageContentPart | FileContentPart;

/** A single message in a chat conversation (OpenAI format, extended with parts). */
export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | ContentPart[];
  name?: string;
  tool_call_id?: string;
  /** @deprecated Legacy field for old conversations. */
  attachments?: Attachment[];
}

/** Uploaded file descriptor. */
export interface Attachment {
  id: string;
  name: string;
  size: number;
  mime: string;
  url: string;
  kind: "image" | "pdf" | "file";
}

/** Request body for /v1/chat/completions (subset of OpenAI spec). */
export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  stream?: boolean;
  /** OpenRouter-style: routing fallback. Ignored, kept for compat. */
  route?: string;
  /** Extra Arena-specific options. */
  arena?: {
    /** Override the timeout (ms) for the browser round-trip. */
    timeout_ms?: number;
    /** Skip the cached session and force a fresh login check. */
    fresh_session?: boolean;
  };
}

/** A single choice in the completion response. */
export interface ChatChoice {
  index: number;
  message: ChatMessage;
  finish_reason: "stop" | "length" | "tool_calls" | "error";
}

/** Usage statistics (best-effort, since Arena does not expose tokens). */
export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/** Response body for /v1/chat/completions (OpenAI format). */
export interface ChatCompletionResponse {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  choices: ChatChoice[];
  usage: ChatUsage;
  system_fingerprint: string;
}

/** A model entry in the registry. */
export interface ArenaModel {
  /** The model id exposed through the OpenAI-compatible API. */
  id: string;
  /** Display label shown in arena.ai's model picker. */
  arena_label: string;
  /** Provider, used for grouping in /v1/models. */
  provider: string;
  /** Human-readable description. */
  description?: string;
  /** Whether the model supports thinking/reasoning traces. */
  thinking?: boolean;
  /** Whether the model accepts image inputs. */
  vision?: boolean;
}

/** Status of the browser session. */
export interface SessionStatus {
  /** Whether a saved browser session (cookies + localStorage) exists. */
  has_saved_session: boolean;
  /** Whether arena.ai currently shows the user as logged in. */
  logged_in: boolean;
  /** Detected username/email if logged in. */
  user_identifier?: string;
  /** Last time the session was verified. */
  last_verified_at?: string;
  /** Last error encountered during session check. */
  last_error?: string;
}

/** A file to be attached to the outgoing message on arena.ai. */
export interface ArenaAttachmentFile {
  /** Absolute local path to the file on the server (passed to Playwright setInputFiles). */
  path: string;
  /** Original filename (used for logging/UI). */
  name: string;
  /** MIME type (e.g. image/png, application/pdf). */
  mime: string;
}

/** Internal result of running one browser-driven chat turn. */
export interface BrowserChatResult {
  text: string;
  model_used: string;
  elapsed_ms: number;
  trace_id?: string;
  /** Whether a captcha/login wall was hit. */
  blocked: boolean;
  block_reason?: "login_required" | "captcha" | "rate_limit" | "unknown";
}

/** A pending entry in the in-memory request queue. */
export interface QueueEntry {
  id: string;
  enqueued_at: number;
  started_at?: number;
  completed_at?: number;
  status: "pending" | "running" | "done" | "error";
  model: string;
  prompt_preview: string;
  result?: BrowserChatResult;
  error?: string;
}
