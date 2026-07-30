# AIOS v11.25.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. GraphRAG & Entity Memory Fusion Engine (`GraphRAGEngine`)
- Added `GraphRAGEngine` in `aios_core/graph_rag.py`.
- Fuses KnowledgeGraph entity triples and VectorStore embeddings for multi-hop RAG context queries.
- REST API: `POST /api/ai/graph-rag/query`.
- SDK: `ai_query_graph_rag()`.

---

## Test Suite Status
- **4372 passed, 0 failed**
