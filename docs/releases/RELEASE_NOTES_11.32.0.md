# AIOS v11.32.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Causal AI & Counterfactual Reasoning Engine (`CausalCounterfactualEngine`)
- Added `CausalCounterfactualEngine` in `aios_core/causal_counterfactual.py`.
- Evaluates causal impact and counterfactual "What-If" scenarios before agent execution.
- REST API: `POST /api/ai/causal/what-if`.
- SDK: `ai_evaluate_what_if()`.

---

## Test Suite Status
- **4389 passed, 0 failed**
