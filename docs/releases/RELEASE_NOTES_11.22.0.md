# AIOS v11.22.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Multi-Provider LLM Router & Fallback Matrix (`LLMRouter`)
- Added `LLMRouter` in `aios_core/llm_router.py` supporting OpenAI, Anthropic, Gemini, DeepSeek, Ollama/vLLM, and Mock providers.
- Automatic fallback chain execution upon provider rate-limit or API failure.
- Integrates with `RollingEnergyBudget` to account for LLM token API costs.

### 2. RAG & Neural Context Augmentation (`ContextAugmenter`)
- Added `ContextAugmenter` in `aios_core/rag_augmentation.py`.
- Enriches agent prompts with semantically relevant memories from `AgentMemorySystem`, vector chunks from `VectorStore`, and entity relationships from `KnowledgeGraph`.

### 3. Multi-Model Swarm Consensus Engine (`SwarmConsensusEngine`)
- Added `SwarmConsensusEngine` in `aios_core/swarm_consensus.py`.
- Queries multiple LLM providers, evaluates response agreement scores, and returns winning consensus decisions.

### 4. REST API & Developer SDK Integration
- Added endpoints:
  - `POST /api/ai/generate`
  - `POST /api/ai/augment`
  - `POST /api/ai/consensus`
- Added SDK methods `ai_generate()`, `ai_augment()`, and `ai_consensus()` to `AIOSClient` and `AIOSClientSync`.

---

## Test Suite Status
- **4364 passed, 0 failed**
