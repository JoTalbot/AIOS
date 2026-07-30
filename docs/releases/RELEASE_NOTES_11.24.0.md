# AIOS v11.24.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. AI Task Planner & Multi-Step Agentic Reasoning (`AITaskPlanner`)
- Added `AITaskPlanner` in `aios_core/ai_planner.py`.
- Decomposes high-level goals into dependency-directed task graphs (`TaskGraph`).
- Supports self-correction and plan replanning upon step execution failures (`self_correct_plan`).
- REST API: `POST /api/ai/plan/decompose` & `POST /api/ai/plan/correct`.
- SDK: `ai_decompose_goal()` & `ai_correct_plan()`.

---

## Test Suite Status
- **4370 passed, 0 failed**
