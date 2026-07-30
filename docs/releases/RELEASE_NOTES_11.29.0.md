# AIOS v11.29.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Self-Evolving Prompt Optimizer (`SelfEvolvingPromptOptimizer`)
- Added `SelfEvolvingPromptOptimizer` in `aios_core/prompt_optimizer.py`.
- Iteratively optimizes prompt instructions to maximize evaluation metrics (accuracy, conciseness).
- REST API: `POST /api/ai/prompt/optimize`.
- SDK: `ai_optimize_prompt()`.

---

## Test Suite Status
- **4380 passed, 0 failed**
