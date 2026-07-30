import type { ArenaModel } from "./types";

/**
 * Registry of models available on arena.ai's Direct Chat picker.
 *
 * Each entry maps an OpenAI-style id (e.g. "gpt-5.2") to the exact label
 * shown in arena.ai's model dropdown, so the browser automation layer can
 * locate and click the right option.
 *
 * Labels were captured from the live arena.ai picker (2026-07-12). If
 * arena.ai changes labels, this registry is the single source to update.
 */
export const ARENA_MODELS: ArenaModel[] = [
  // ─── OpenAI ────────────────────────────────────────────────────────────
  {
    id: "gpt-5.5-instant",
    arena_label: "gpt-5.5-instant",
    provider: "OpenAI",
    description: "Fast variant of GPT-5.5 for instant replies.",
  },
  {
    id: "gpt-5.2-high",
    arena_label: "gpt-5.2-high",
    provider: "OpenAI",
    description: "GPT-5.2 with high reasoning effort.",
    thinking: true,
  },
  {
    id: "gpt-5.2",
    arena_label: "gpt-5.2",
    provider: "OpenAI",
    description: "Standard GPT-5.2 model.",
  },
  {
    id: "gpt-5.2-chat-latest",
    arena_label: "gpt-5.2-chat-latest",
    provider: "OpenAI",
    description: "Latest GPT-5.2 chat-tuned snapshot.",
  },
  {
    id: "gpt-5.1-high",
    arena_label: "gpt-5.1-high",
    provider: "OpenAI",
    description: "GPT-5.1 with high reasoning effort.",
    thinking: true,
  },
  {
    id: "gpt-5.1",
    arena_label: "gpt-5.1",
    provider: "OpenAI",
    description: "Standard GPT-5.1 model.",
  },
  {
    id: "gpt-5.4-mini-high",
    arena_label: "gpt-5.4-mini-high",
    provider: "OpenAI",
    description: "Compact GPT-5.4 with high reasoning.",
    thinking: true,
  },
  {
    id: "gpt-5.4-nano-high",
    arena_label: "gpt-5.4-nano-high",
    provider: "OpenAI",
    description: "Smallest GPT-5.4 variant, high reasoning.",
    thinking: true,
  },
  {
    id: "gpt-5.3-chat-latest",
    arena_label: "gpt-5.3-chat-latest",
    provider: "OpenAI",
    description: "Latest GPT-5.3 chat snapshot.",
  },
  {
    id: "gpt-5-high",
    arena_label: "gpt-5-high",
    provider: "OpenAI",
    description: "GPT-5 with high reasoning effort.",
    thinking: true,
  },
  {
    id: "gpt-5-chat",
    arena_label: "gpt-5-chat",
    provider: "OpenAI",
    description: "GPT-5 chat-tuned default.",
  },
  {
    id: "gpt-5-mini-high",
    arena_label: "gpt-5-mini-high",
    provider: "OpenAI",
    description: "Mini GPT-5 with high reasoning.",
    thinking: true,
  },
  {
    id: "gpt-5-nano-high",
    arena_label: "gpt-5-nano-high",
    provider: "OpenAI",
    description: "Nano GPT-5 with high reasoning.",
    thinking: true,
  },
  {
    id: "gpt-5-high-new-system-prompt",
    arena_label: "gpt-5-high-new-system-prompt",
    provider: "OpenAI",
    description: "GPT-5 high with experimental system prompt.",
    thinking: true,
  },
  {
    id: "gpt-4.1",
    arena_label: "gpt-4.1-2025-04-14",
    provider: "OpenAI",
    description: "GPT-4.1 (April 2025 snapshot).",
  },
  {
    id: "gpt-4.1-mini",
    arena_label: "gpt-4.1-mini-2025-04-14",
    provider: "OpenAI",
    description: "GPT-4.1 mini (April 2025 snapshot).",
  },
  {
    id: "o3",
    arena_label: "o3-2025-04-16",
    provider: "OpenAI",
    description: "OpenAI o3 reasoning model.",
    thinking: true,
  },
  {
    id: "o3-mini",
    arena_label: "o3-mini",
    provider: "OpenAI",
    description: "Compact o3 reasoning model.",
    thinking: true,
  },
  {
    id: "o4-mini",
    arena_label: "o4-mini-2025-04-16",
    provider: "OpenAI",
    description: "Compact o4 reasoning model.",
    thinking: true,
  },

  // ─── Google Gemini ─────────────────────────────────────────────────────
  {
    id: "gemini-3.5-flash-high",
    arena_label: "gemini-3.5-flash-high",
    provider: "Google",
    description: "Gemini 3.5 Flash with high reasoning.",
    thinking: true,
  },
  {
    id: "gemini-3.5-flash",
    arena_label: "gemini-3.5-flash",
    provider: "Google",
    description: "Gemini 3.5 Flash.",
  },
  {
    id: "gemini-3.1-pro-preview",
    arena_label: "gemini-3.1-pro-preview",
    provider: "Google",
    description: "Gemini 3.1 Pro preview.",
  },
  {
    id: "gemini-3-flash",
    arena_label: "gemini-3-flash",
    provider: "Google",
    description: "Gemini 3 Flash.",
  },
  {
    id: "gemini-3-flash-thinking-minimal",
    arena_label: "gemini-3-flash (thinking-minimal)",
    provider: "Google",
    description: "Gemini 3 Flash with minimal thinking.",
    thinking: true,
  },
  {
    id: "gemini-3.1-flash-lite",
    arena_label: "gemini-3.1-flash-lite",
    provider: "Google",
    description: "Lightweight Gemini 3.1 Flash.",
  },
  {
    id: "gemini-2.5-pro",
    arena_label: "gemini-2.5-pro",
    provider: "Google",
    description: "Gemini 2.5 Pro.",
  },
  {
    id: "gemini-2.5-flash",
    arena_label: "gemini-2.5-flash",
    provider: "Google",
    description: "Gemini 2.5 Flash.",
  },
  {
    id: "gemini-2.0-flash",
    arena_label: "gemini-2.0-flash-001",
    provider: "Google",
    description: "Gemini 2.0 Flash.",
  },

  // ─── Anthropic Claude ──────────────────────────────────────────────────
  {
    id: "claude-sonnet-5-high",
    arena_label: "Anthropic claude-sonnet-5-high",
    provider: "Anthropic",
    description: "Claude Sonnet 5 with high reasoning.",
    thinking: true,
  },
  {
    id: "claude-sonnet-4-6",
    arena_label: "Anthropic claude-sonnet-4-6",
    provider: "Anthropic",
    description: "Claude Sonnet 4.6.",
  },
  {
    id: "claude-sonnet-4-5-20250929",
    arena_label: "Anthropic claude-sonnet-4-5-20250929",
    provider: "Anthropic",
    description: "Claude Sonnet 4.5 (Sep 2025).",
  },
  {
    id: "claude-sonnet-4-5-thinking",
    arena_label: "Anthropic claude-sonnet-4-5-20250929-thinking-32k",
    provider: "Anthropic",
    description: "Claude Sonnet 4.5 with 32k thinking budget.",
    thinking: true,
  },
  {
    id: "claude-haiku-4-5",
    arena_label: "Anthropic claude-haiku-4-5-20251001",
    provider: "Anthropic",
    description: "Claude Haiku 4.5 (Oct 2025).",
  },
  {
    id: "claude-sonnet-4-20250514",
    arena_label: "Anthropic claude-sonnet-4-20250514",
    provider: "Anthropic",
    description: "Claude Sonnet 4 (May 2024).",
  },
  {
    id: "claude-sonnet-4-thinking",
    arena_label: "Anthropic claude-sonnet-4-20250514-thinking-32k",
    provider: "Anthropic",
    description: "Claude Sonnet 4 with 32k thinking budget.",
    thinking: true,
  },

  // ─── xAI Grok ──────────────────────────────────────────────────────────
  {
    id: "grok-4.20-reasoning",
    arena_label: "grok-4.20-beta-0309-reasoning",
    provider: "xAI",
    description: "Grok 4.20 reasoning beta.",
    thinking: true,
  },
  {
    id: "grok-4.20-multi-agent",
    arena_label: "grok-4.20-multi-agent-beta-0309",
    provider: "xAI",
    description: "Grok 4.20 multi-agent beta.",
  },
  {
    id: "grok-4.5",
    arena_label: "grok-4.5",
    provider: "xAI",
    description: "Grok 4.5.",
  },
  {
    id: "grok-4.3",
    arena_label: "grok-4.3",
    provider: "xAI",
    description: "Grok 4.3.",
  },

  // ─── DeepSeek ──────────────────────────────────────────────────────────
  {
    id: "deepseek-v4-pro-thinking",
    arena_label: "deepseek-v4-pro-thinking",
    provider: "DeepSeek",
    description: "DeepSeek V4 Pro with thinking.",
    thinking: true,
  },
  {
    id: "deepseek-v4-pro",
    arena_label: "deepseek-v4-pro",
    provider: "DeepSeek",
    description: "DeepSeek V4 Pro.",
  },
  {
    id: "deepseek-v4-flash-thinking",
    arena_label: "deepseek-v4-flash-thinking",
    provider: "DeepSeek",
    description: "DeepSeek V4 Flash with thinking.",
    thinking: true,
  },
  {
    id: "deepseek-v4-flash",
    arena_label: "deepseek-v4-flash",
    provider: "DeepSeek",
    description: "DeepSeek V4 Flash.",
  },

  // ─── Qwen (Alibaba) ────────────────────────────────────────────────────
  {
    id: "qwen3.7-max",
    arena_label: "qwen3.7-max",
    provider: "Alibaba",
    description: "Qwen 3.7 Max.",
  },
  {
    id: "qwen3.7-plus",
    arena_label: "qwen3.7-plus",
    provider: "Alibaba",
    description: "Qwen 3.7 Plus.",
  },
  {
    id: "qwen3.7-max-preview",
    arena_label: "qwen3.7-max-preview",
    provider: "Alibaba",
    description: "Qwen 3.7 Max preview.",
  },
  {
    id: "qwen3.7-plus-preview",
    arena_label: "qwen3.7-plus-preview",
    provider: "Alibaba",
    description: "Qwen 3.7 Plus preview.",
  },
  {
    id: "qwen3.6-max-preview",
    arena_label: "qwen3.6-max-preview",
    provider: "Alibaba",
    description: "Qwen 3.6 Max preview.",
  },
  {
    id: "qwen3.6-plus",
    arena_label: "qwen3.6-plus",
    provider: "Alibaba",
    description: "Qwen 3.6 Plus.",
  },
  {
    id: "qwen3.6-27b",
    arena_label: "qwen3.6-27b",
    provider: "Alibaba",
    description: "Qwen 3.6 27B open weights.",
  },
  {
    id: "qwen3.5-max-preview",
    arena_label: "qwen3.5-max-preview",
    provider: "Alibaba",
    description: "Qwen 3.5 Max preview.",
  },
  {
    id: "qwen3.5-flash",
    arena_label: "qwen3.5-flash",
    provider: "Alibaba",
    description: "Qwen 3.5 Flash.",
  },
  {
    id: "qwen3.5-27b",
    arena_label: "qwen3.5-27b",
    provider: "Alibaba",
    description: "Qwen 3.5 27B open weights.",
  },
  {
    id: "qwen3.5-122b",
    arena_label: "qwen3.5-122b-a10b",
    provider: "Alibaba",
    description: "Qwen 3.5 122B (A10B MoE).",
  },
  {
    id: "qwen3.5-397b",
    arena_label: "qwen3.5-397b-a17b",
    provider: "Alibaba",
    description: "Qwen 3.5 397B (A17B MoE).",
  },
  {
    id: "qwen3.5-35b",
    arena_label: "qwen3.5-35b-a3b",
    provider: "Alibaba",
    description: "Qwen 3.5 35B (A3B MoE).",
  },
  {
    id: "qwen3-max-thinking",
    arena_label: "qwen3-max-thinking",
    provider: "Alibaba",
    description: "Qwen 3 Max with thinking.",
    thinking: true,
  },
  {
    id: "qwen3-max-2025-09-23",
    arena_label: "qwen3-max-2025-09-23",
    provider: "Alibaba",
    description: "Qwen 3 Max (Sep 23, 2025).",
  },
  {
    id: "qwen3-max-2025-09-26",
    arena_label: "qwen3-max-2025-09-26",
    provider: "Alibaba",
    description: "Qwen 3 Max (Sep 26, 2025).",
  },
  {
    id: "qwen3-235b-a22b-instruct",
    arena_label: "qwen3-235b-a22b-instruct-2507",
    provider: "Alibaba",
    description: "Qwen 3 235B (A22B) instruct.",
  },
  {
    id: "qwen3-235b-a22b-thinking",
    arena_label: "qwen3-235b-a22b-thinking-2507",
    provider: "Alibaba",
    description: "Qwen 3 235B (A22B) thinking.",
    thinking: true,
  },
  {
    id: "qwen3-235b-a22b-no-thinking",
    arena_label: "qwen3-235b-a22b-no-thinking",
    provider: "Alibaba",
    description: "Qwen 3 235B (A22B) no-thinking.",
  },
  {
    id: "qwen3-235b-a22b",
    arena_label: "qwen3-235b-a22b",
    provider: "Alibaba",
    description: "Qwen 3 235B (A22B) base.",
  },
  {
    id: "qwen3-next-80b-instruct",
    arena_label: "qwen3-next-80b-a3b-instruct",
    provider: "Alibaba",
    description: "Qwen 3 Next 80B (A3B) instruct.",
  },
  {
    id: "qwen3-next-80b-thinking",
    arena_label: "qwen3-next-80b-a3b-thinking",
    provider: "Alibaba",
    description: "Qwen 3 Next 80B (A3B) thinking.",
    thinking: true,
  },
  {
    id: "qwen3-30b-a3b-instruct",
    arena_label: "qwen3-30b-a3b-instruct-2507",
    provider: "Alibaba",
    description: "Qwen 3 30B (A3B) instruct.",
  },
  {
    id: "qwen3-30b-a3b",
    arena_label: "qwen3-30b-a3b",
    provider: "Alibaba",
    description: "Qwen 3 30B (A3B) base.",
  },
  {
    id: "qwen3-coder-480b",
    arena_label: "qwen3-coder-480b-a35b-instruct",
    provider: "Alibaba",
    description: "Qwen 3 Coder 480B (A35B) instruct.",
  },
  {
    id: "qwen3-vl-235b-instruct",
    arena_label: "qwen3-vl-235b-a22b-instruct",
    provider: "Alibaba",
    description: "Qwen 3 VL 235B instruct.",
    vision: true,
  },
  {
    id: "qwen3-vl-235b-thinking",
    arena_label: "qwen3-vl-235b-a22b-thinking",
    provider: "Alibaba",
    description: "Qwen 3 VL 235B thinking.",
    thinking: true,
    vision: true,
  },
  {
    id: "qwen3-vl-8b-instruct",
    arena_label: "qwen3-vl-8b-instruct",
    provider: "Alibaba",
    description: "Qwen 3 VL 8B instruct.",
    vision: true,
  },
  {
    id: "qwen3-vl-8b-thinking",
    arena_label: "qwen3-vl-8b-thinking",
    provider: "Alibaba",
    description: "Qwen 3 VL 8B thinking.",
    thinking: true,
    vision: true,
  },
  {
    id: "qwen3-omni-flash",
    arena_label: "qwen3-omni-flash",
    provider: "Alibaba",
    description: "Qwen 3 Omni Flash multimodal.",
    vision: true,
  },
  {
    id: "qwq-32b",
    arena_label: "qwq-32b",
    provider: "Alibaba",
    description: "QwQ 32B reasoning.",
    thinking: true,
  },
  {
    id: "qwen-vl-max",
    arena_label: "qwen-vl-max-2025-08-13",
    provider: "Alibaba",
    description: "Qwen VL Max (Aug 2025).",
    vision: true,
  },

  // ─── Zhipu GLM ─────────────────────────────────────────────────────────
  {
    id: "glm-5.2-max",
    arena_label: "glm-5.2 (max)",
    provider: "Zhipu",
    description: "GLM 5.2 Max.",
  },
  {
    id: "glm-5.1",
    arena_label: "glm-5.1",
    provider: "Zhipu",
    description: "GLM 5.1.",
  },
  {
    id: "glm-5",
    arena_label: "glm-5",
    provider: "Zhipu",
    description: "GLM 5.",
  },
  {
    id: "glm-4.7",
    arena_label: "glm-4.7",
    provider: "Zhipu",
    description: "GLM 4.7.",
  },
  {
    id: "glm-5v-turbo",
    arena_label: "glm-5v-turbo",
    provider: "Zhipu",
    description: "GLM 5V Turbo multimodal.",
    vision: true,
  },

  // ─── Kimi (Moonshot) ───────────────────────────────────────────────────
  {
    id: "kimi-k2.6",
    arena_label: "kimi-k2.6",
    provider: "Moonshot",
    description: "Kimi K2.6.",
  },
  {
    id: "kimi-k2.5-instant",
    arena_label: "kimi-k2.5-instant",
    provider: "Moonshot",
    description: "Kimi K2.5 Instant.",
  },
  {
    id: "kimi-k2.5-thinking",
    arena_label: "kimi-k2.5-thinking",
    provider: "Moonshot",
    description: "Kimi K2.5 Thinking.",
    thinking: true,
  },
  {
    id: "kimi-k2-thinking-turbo",
    arena_label: "kimi-k2-thinking-turbo",
    provider: "Moonshot",
    description: "Kimi K2 Thinking Turbo.",
    thinking: true,
  },
  {
    id: "kimi-k2-0905-preview",
    arena_label: "kimi-k2-0905-preview",
    provider: "Moonshot",
    description: "Kimi K2 (Sep 5 preview).",
  },
  {
    id: "kimi-k2-0711-preview",
    arena_label: "kimi-k2-0711-preview",
    provider: "Moonshot",
    description: "Kimi K2 (Jul 11 preview).",
  },

  // ─── MiniMax ───────────────────────────────────────────────────────────
  {
    id: "minimax-m3",
    arena_label: "minimax-m3",
    provider: "MiniMax",
    description: "MiniMax M3.",
  },
  {
    id: "minimax-m2.7",
    arena_label: "minimax-m2.7",
    provider: "MiniMax",
    description: "MiniMax M2.7.",
  },
  {
    id: "minimax-m2.5",
    arena_label: "minimax-m2.5",
    provider: "MiniMax",
    description: "MiniMax M2.5.",
  },
  {
    id: "minimax-m2.1-preview",
    arena_label: "minimax-m2.1-preview",
    provider: "MiniMax",
    description: "MiniMax M2.1 preview.",
  },
  {
    id: "minimax-m2-preview",
    arena_label: "minimax-m2-preview",
    provider: "MiniMax",
    description: "MiniMax M2 preview.",
  },
  {
    id: "minimax-m2",
    arena_label: "minimax-m2",
    provider: "MiniMax",
    description: "MiniMax M2.",
  },
  {
    id: "minimax-m1",
    arena_label: "minimax-m1",
    provider: "MiniMax",
    description: "MiniMax M1.",
  },

  // ─── Mistral ───────────────────────────────────────────────────────────
  {
    id: "mistral-large-3",
    arena_label: "mistral-large-3",
    provider: "Mistral",
    description: "Mistral Large 3.",
  },
  {
    id: "mistral-medium-3.5",
    arena_label: "mistral-medium-3.5",
    provider: "Mistral",
    description: "Mistral Medium 3.5.",
  },
  {
    id: "mistral-medium-2508",
    arena_label: "mistral-medium-2508",
    provider: "Mistral",
    description: "Mistral Medium (Aug 2025).",
  },

  // ─── ByteDance Doubao ──────────────────────────────────────────────────
  {
    id: "doubao-seed-2.0-vision",
    arena_label: "Bytedance dola-seed-2.0-preview-vision",
    provider: "ByteDance",
    description: "Doubao Seed 2.0 vision preview.",
    vision: true,
  },
  {
    id: "doubao-seed-2.0-text",
    arena_label: "Bytedance dola-seed-2.0-preview-text",
    provider: "ByteDance",
    description: "Doubao Seed 2.0 text preview.",
  },

  // ─── Tencent ───────────────────────────────────────────────────────────
  {
    id: "hunyuan-vision-1.5-thinking",
    arena_label: "Tencent hunyuan-vision-1.5-thinking",
    provider: "Tencent",
    description: "Hunyuan Vision 1.5 thinking.",
    thinking: true,
    vision: true,
  },
  {
    id: "tencent-hy3",
    arena_label: "Tencent hy3",
    provider: "Tencent",
    description: "Tencent HY3.",
  },

  // ─── Xiaomi MiMo ───────────────────────────────────────────────────────
  {
    id: "mimo-v2-omni",
    arena_label: "mimo-v2-omni",
    provider: "Xiaomi",
    description: "MiMo V2 Omni.",
    vision: true,
  },
  {
    id: "mimo-v2.5-pro",
    arena_label: "mimo-v2.5-pro",
    provider: "Xiaomi",
    description: "MiMo V2.5 Pro.",
  },
  {
    id: "mimo-v2.5",
    arena_label: "mimo-v2.5",
    provider: "Xiaomi",
    description: "MiMo V2.5.",
  },
  {
    id: "mimo-v2-flash-thinking",
    arena_label: "mimo-v2-flash (thinking)",
    provider: "Xiaomi",
    description: "MiMo V2 Flash (thinking).",
    thinking: true,
  },
  {
    id: "mimo-v2-flash",
    arena_label: "mimo-v2-flash",
    provider: "Xiaomi",
    description: "MiMo V2 Flash.",
  },

  // ─── StepFun ───────────────────────────────────────────────────────────
  {
    id: "step-3.5-flash",
    arena_label: "Stepfun step-3.5-flash",
    provider: "StepFun",
    description: "Step 3.5 Flash.",
  },

  // ─── Baidu ─────────────────────────────────────────────────────────────
  {
    id: "ernie-5.0-preview",
    arena_label: "ernie-5.0-preview-1220",
    provider: "Baidu",
    description: "ERNIE 5.0 preview (Dec 20).",
  },

  // ─── Open weights / research models ────────────────────────────────────
  {
    id: "gemma-4-31b",
    arena_label: "gemma-4-31b",
    provider: "Google",
    description: "Gemma 4 31B open weights.",
  },
  {
    id: "gemma-4-26b-a4b",
    arena_label: "gemma-4-26b-a4b",
    provider: "Google",
    description: "Gemma 4 26B (A4B MoE).",
  },
  {
    id: "gemma-3-27b-it",
    arena_label: "gemma-3-27b-it",
    provider: "Google",
    description: "Gemma 3 27B instruction-tuned.",
  },
  {
    id: "gemma-3n-e4b-it",
    arena_label: "gemma-3n-e4b-it",
    provider: "Google",
    description: "Gemma 3n E4B instruction-tuned.",
  },
  {
    id: "deepseek-r1-distill-llama-70b",
    arena_label: "intellect-3",
    provider: "PrimeIntellect",
    description: "Intellect-3 open weights.",
  },
  {
    id: "gpt-oss-120b",
    arena_label: "gpt-oss-120b",
    provider: "OpenAI",
    description: "GPT-OSS 120B open weights.",
  },
  {
    id: "gpt-oss-20b",
    arena_label: "gpt-oss-20b",
    provider: "OpenAI",
    description: "GPT-OSS 20B open weights.",
  },
  {
    id: "nova-2-lite",
    arena_label: "nova-2-lite",
    provider: "Amazon",
    description: "Amazon Nova 2 Lite.",
  },
  {
    id: "amazon-nova-pro",
    arena_label: "amazon.nova-pro-v1:0",
    provider: "Amazon",
    description: "Amazon Nova Pro v1.0.",
  },
  {
    id: "qwq-32b-nvidia",
    arena_label: "nvidia-nemotron-3-nano-30b-a3b-bf16",
    provider: "NVIDIA",
    description: "NVIDIA Nemotron 3 Nano 30B (A3B).",
  },
  {
    id: "nvidia-nemotron-3-super-120b",
    arena_label: "nvidia-nemotron-3-super-120b-a12b",
    provider: "NVIDIA",
    description: "NVIDIA Nemotron 3 Super 120B (A12B).",
  },
  {
    id: "nvidia-nemotron-3-ultra-550b",
    arena_label: "nvidia-nemotron-3-ultra-550b-a55b-nvfp4",
    provider: "NVIDIA",
    description: "NVIDIA Nemotron 3 Ultra 550B (A55B).",
  },
  {
    id: "granite-4.1-8b",
    arena_label: "granite-4.1-8b",
    provider: "IBM",
    description: "IBM Granite 4.1 8B.",
  },
  {
    id: "ibm-granite-h-small",
    arena_label: "ibm-granite-h-small",
    provider: "IBM",
    description: "IBM Granite H Small.",
  },
  {
    id: "mercury-2",
    arena_label: "mercury-2",
    provider: "Inception",
    description: "Mercury 2 diffusion LLM.",
  },
  {
    id: "mercury",
    arena_label: "mercury",
    provider: "Inception",
    description: "Mercury diffusion LLM.",
  },
  {
    id: "ling-flash-2.0",
    arena_label: "ling-flash-2.0",
    provider: "InclusionAI",
    description: "Ling Flash 2.0 open weights.",
  },
  {
    id: "ling-2.5-1t",
    arena_label: "ling-2.5-1t",
    provider: "InclusionAI",
    description: "Ling 2.5 1T open weights.",
  },
  {
    id: "ring-flash-2.0",
    arena_label: "ring-flash-2.0",
    provider: "InclusionAI",
    description: "Ring Flash 2.0 open weights.",
  },
  {
    id: "ring-2.5-1t",
    arena_label: "ring-2.5-1t",
    provider: "InclusionAI",
    description: "Ring 2.5 1T open weights.",
  },
  {
    id: "longcat-flash-chat",
    arena_label: "longcat-flash-chat",
    provider: "Meituan",
    description: "LongCat Flash chat.",
  },
  {
    id: "longcat-2.0",
    arena_label: "longcat-2.0",
    provider: "Meituan",
    description: "LongCat 2.0.",
  },
  {
    id: "trinity-large-preview",
    arena_label: "trinity-large-preview",
    provider: "Trinity",
    description: "Trinity Large preview.",
  },
  {
    id: "trinity-large-thinking",
    arena_label: "trinity-large-thinking",
    provider: "Trinity",
    description: "Trinity Large thinking.",
    thinking: true,
  },
];

/** Lookup map by model id. */
export const MODEL_BY_ID: Map<string, ArenaModel> = new Map(
  ARENA_MODELS.map((m) => [m.id, m]),
);

/** Find a model by id, falling back to case-insensitive match. */
export function findModel(id: string): ArenaModel | undefined {
  if (MODEL_BY_ID.has(id)) return MODEL_BY_ID.get(id);
  const lower = id.toLowerCase();
  return ARENA_MODELS.find((m) => m.id.toLowerCase() === lower);
}

/** Distinct provider list (sorted). */
export function listProviders(): string[] {
  return Array.from(new Set(ARENA_MODELS.map((m) => m.provider))).sort();
}

/** Flat list of all arena.ai labels (used for fuzzy button matching). */
export const ALL_ARENA_LABELS: string[] = ARENA_MODELS.map((m) => m.arena_label);
