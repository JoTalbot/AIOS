# AIOS v11.26.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Self-Supervised Knowledge Distillation & Fine-Tuning Engine (`KnowledgeDistillationEngine`)
- Added `KnowledgeDistillationEngine` in `aios_core/knowledge_distillation.py`.
- Collects high-scoring agent execution trajectories and prepares JSONL datasets for local model fine-tuning and distillation.
- REST API: `POST /api/ai/distillation/collect` & `POST /api/ai/distillation/dataset`.
- SDK: `ai_collect_trajectory()` & `ai_prepare_distillation_dataset()`.

---

## Test Suite Status
- **4374 passed, 0 failed**
