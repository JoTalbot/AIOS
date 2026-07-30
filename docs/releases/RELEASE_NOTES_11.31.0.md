# AIOS v11.31.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Autonomous Neural Memory Consolidation & Vector Index Auto-Compaction (`NeuralMemoryConsolidator`)
- Added `NeuralMemoryConsolidator` in `aios_core/neural_memory_consolidation.py`.
- Clusters short-term agent memories, extracts core knowledge patterns into long-term vector store, and compacts vector index noise.
- REST API: `POST /api/ai/memory/consolidate-neural`.
- SDK: `ai_consolidate_neural_memory()`.

---

## Test Suite Status
- **4388 passed, 0 failed**
