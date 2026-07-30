/**
 * Chat types for the Arena Router web chat.
 *
 * A conversation is a sequence of messages with a selected model and an
 * optional system prompt. Conversations persist to localStorage so the
 * user can switch between them without losing context.
 */

export type Role = "user" | "assistant" | "system";

/** Uploaded file descriptor. */
export interface Attachment {
  id: string;
  name: string;
  size: number;
  mime: string;
  url: string;
  kind: "image" | "pdf" | "file";
}

/** A single content part (multimodal). */
export type ContentPart =
  | { type: "text"; text: string }
  | { type: "image_url"; image_url: { url: string; detail?: "auto" | "low" | "high" } }
  | { type: "file"; file: { url: string; name: string; mime: string; size?: number } };

export interface ChatMessage {
  id: string;
  role: Role;
  content: string | ContentPart[];
  /** Attachments for user messages (shorthand rendered in UI; content is derived from it). */
  attachments?: Attachment[];
  /** Which model generated this (for assistant messages). */
  model?: string;
  /** When the message was created (epoch ms). */
  timestamp: number;
  /** True while the assistant message is being streamed. */
  streaming?: boolean;
  /** Error message if generation failed. */
  error?: string;
  /** How long generation took (ms, for assistant messages). */
  elapsed_ms?: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  /** Currently selected model id (applies to the next assistant turn). */
  model: string;
  /** Optional system prompt for this conversation. */
  systemPrompt?: string;
  /** Optional agent preset id (drives system prompt + suggested model). */
  agentPresetId?: string;
  createdAt: number;
  updatedAt: number;
}

/** Preset agent personas — quick-start templates for common tasks. */
export interface AgentPreset {
  id: string;
  name: string;
  description: string;
  icon: string;
  systemPrompt: string;
  suggestedModel: string;
  /** Suggested opening user message (optional). */
  starterPrompt?: string;
}

export const AGENT_PRESETS: AgentPreset[] = [
  {
    id: "general",
    name: "General Assistant",
    description: "Universal assistant for any task",
    icon: "Sparkles",
    systemPrompt: "You are a helpful, concise assistant. Answer clearly and ask for clarification when needed.",
    suggestedModel: "gpt-5.2",
  },
  {
    id: "octopus-agent",
    name: "Octopus Agent",
    description: "Octopus-skills-aware operational agent",
    icon: "Boxes",
    systemPrompt:
      "Ты — агент Octopus, помогающий с операционными задачами кластера. " +
      "Отвечай на русском. Используй контекст навыков Octopus (skills, MCP, integrations). " +
      "Если задача требует выполнения команды — предложи команду в блоке ```bash. " +
      "Соблюдай bounded-режим: один безопасный шаг за цикл.",
    suggestedModel: "gpt-5.2-high",
    starterPrompt: "Проверь состояние кластера и предложи следующий bounded-шаг.",
  },
  {
    id: "coder",
    name: "Code Engineer",
    description: "Production-grade code generation and review",
    icon: "Code",
    systemPrompt:
      "You are a senior software engineer. Write production-quality code with:\n" +
      "- Clear error handling\n" +
      "- Type annotations\n" +
      "- Concise comments where needed\n" +
      "- Tests for critical paths\n" +
      "Prefer the simplest correct solution. Explain trade-offs briefly.",
    suggestedModel: "claude-sonnet-4-5-20250929",
    starterPrompt: "Write a Python function that reads a JSON file and validates it against a Pydantic schema.",
  },
  {
    id: "analyst",
    name: "Data Analyst",
    description: "Reasoning-heavy analysis and reporting",
    icon: "Brain",
    systemPrompt:
      "You are a meticulous data analyst. Think step by step. " +
      "Structure your answer with: 1) Assumptions, 2) Analysis, 3) Findings, 4) Recommendations. " +
      "When unsure, say so explicitly. Prefer concrete numbers over vague statements.",
    suggestedModel: "gpt-5.2-high",
    starterPrompt: "Analyze the following metrics and identify the top 3 anomalies:\n\n",
  },
  {
    id: "researcher",
    name: "Research Assistant",
    description: "Long-form research with citations",
    icon: "Search",
    systemPrompt:
      "You are a research assistant. Provide thorough, well-structured answers with:\n" +
      "- Clear section headings\n" +
      "- Bullet points for key findings\n" +
      "- Concrete examples\n" +
      "- Caveats and limitations\n" +
      "Aim for depth over brevity. Mark uncertain claims explicitly.",
    suggestedModel: "gemini-3.1-pro-preview",
    starterPrompt: "Research the current state of browser automation for LLM access.",
  },
  {
    id: "translator",
    name: "Translator (RU/EN)",
    description: "Bilingual translation with cultural context",
    icon: "Languages",
    systemPrompt:
      "You are a professional translator between Russian and English. " +
      "Preserve tone, idioms, and cultural context. " +
      "For technical terms, provide the original in parentheses on first use. " +
      "If the input is Russian, translate to English; if English, translate to Russian.",
    suggestedModel: "gpt-5.2",
  },
  {
    id: "creative",
    name: "Creative Writer",
    description: "Stories, marketing copy, brainstorming",
    icon: "PenTool",
    systemPrompt:
      "You are a creative writer with a flair for vivid imagery and rhythm. " +
      "Adapt your style to the requested genre. For marketing copy, lead with benefits. " +
      "For fiction, show don't tell. For brainstorming, give 5-7 diverse options.",
    suggestedModel: "claude-sonnet-4-5-20250929",
  },
  {
    id: "sql",
    name: "SQL Expert",
    description: "Query optimization and schema design",
    icon: "Database",
    systemPrompt:
      "You are a SQL expert. Write portable SQL (PostgreSQL dialect unless told otherwise). " +
      "Always explain the query plan intuition. Suggest indexes when relevant. " +
      "For schema design, normalize to 3NF unless denormalization is justified.",
    suggestedModel: "gpt-5.2",
    starterPrompt: "Design a schema for a multi-tenant SaaS with organizations, users, and audit log.",
  },
];

/** Map preset id → preset, for quick lookup. */
export const PRESET_BY_ID: Map<string, AgentPreset> = new Map(
  AGENT_PRESETS.map((p) => [p.id, p]),
);
