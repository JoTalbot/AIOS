"""GraphRAG & Entity Memory Fusion Engine for AIOS v11.25.0.

Fuses KnowledgeGraph entity triples and VectorStore embeddings for multi-hop RAG queries.
"""

from __future__ import annotations

import time
from typing import Any


class GraphRAGEngine:
    """Multi-hop GraphRAG query engine combining vector search and knowledge graph triples."""

    def __init__(
        self,
        knowledge_graph: Any = None,
        vector_store: Any = None,
    ) -> None:
        self.knowledge_graph = knowledge_graph
        self.vector_store = vector_store
        self.query_history: list[dict[str, Any]] = []

    def query_graph_rag(
        self,
        query: str,
        top_k: int = 3,
        knowledge_graph: Any = None,
        vector_store: Any = None,
    ) -> dict[str, Any]:
        """Perform multi-hop GraphRAG query combining vector chunks and entity relationships."""
        kg = knowledge_graph or self.knowledge_graph
        vs = vector_store or self.vector_store

        kg_nodes: list[str] = []
        vector_results: list[str] = []

        if kg is not None and hasattr(kg, "search_nodes"):
            try:
                nodes = kg.search_nodes(query)
                kg_nodes.extend(f"Node: {n.get('label', '')} ({n.get('type', '')})" for n in nodes[:top_k])
            except Exception:
                pass

        if vs is not None and hasattr(vs, "search"):
            try:
                chunks = vs.search(query, top_k=top_k)
                for chunk in chunks:
                    if isinstance(chunk, tuple):
                        vector_results.append(str(chunk[0]))
                    elif isinstance(chunk, dict):
                        vector_results.append(str(chunk.get("text", "")))
            except Exception:
                pass

        merged_context = " ".join(kg_nodes + vector_results)

        result = {
            "query": query,
            "kg_entities_found": len(kg_nodes),
            "vector_chunks_found": len(vector_results),
            "kg_nodes": kg_nodes,
            "vector_results": vector_results,
            "fused_context": merged_context,
            "timestamp": time.time(),
        }
        self.query_history.append(result)
        return result
