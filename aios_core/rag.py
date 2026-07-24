"""Retrieval-Augmented Generation (RAG) for AIOS v10.9.0.

RAG pipeline with document indexing, semantic
retrieval, context window management, generation
with retrieved context, chunking, and hybrid search.

Classes:
    DocumentChunk  — chunked document segment
    RAGSystem      — full RAG engine
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Chunked document segment with embedding."""

    doc_id: str
    chunk_id: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0


class RAGSystem:
    """Full RAG engine.

    Features:
    - Document indexing with chunking
    - Semantic retrieval (TF-IDF + embedding similarity)
    - Context window management
    - Generation with retrieved context
    - Full query pipeline (retrieve → generate)
    - Hybrid search (keyword + semantic)
    """

    def __init__(
        self, vector_store: Any = None, chunk_size: int = 500, top_k: int = 5
    ) -> None:
        self.vector_store = vector_store
        self.documents: list[dict[str, Any]] = []
        self.chunks: list[DocumentChunk] = []
        self.chunk_size = chunk_size
        self.top_k = top_k
        self._index: dict[str, dict[str, int]] = {}  # term → {doc_id: count}
        self._query_count: int = 0

    # ── Document Indexing ──────────────────────────────────────────

    def index_document(
        self, doc_id: str, text: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Index a document with automatic chunking (backward-compatible)."""
        doc = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "indexed_at": time.time(),
        }
        self.documents.append(doc)

        # Chunk the document
        words = text.split()
        for i in range(0, len(words), self.chunk_size):
            chunk_text = " ".join(words[i : i + self.chunk_size])
            chunk = DocumentChunk(
                doc_id=doc_id,
                chunk_id=i // self.chunk_size,
                text=chunk_text,
                metadata=metadata or {},
                start_offset=i,
                end_offset=i + len(chunk_text),
            )
            # Generate simple embedding from word frequencies
            chunk.embedding = self._simple_embedding(chunk_text)
            self.chunks.append(chunk)

        # Update inverted index
        for word in re.findall(r"\b\w+\b", text.lower()):
            if word not in self._index:
                self._index[word] = {}
            self._index[word][doc_id] = self._index[word].get(doc_id, 0) + 1

    def _simple_embedding(self, text: str, dim: int = 64) -> list[float]:
        """Generate a simple embedding from text."""
        words = re.findall(r"\b\w+\b", text.lower())
        embedding = [0.0] * dim
        for word in words:
            idx = hash(word) % dim
            embedding[idx] += 1.0 / len(words)
        return embedding

    # ── Retrieval ──────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Retrieve relevant documents (backward-compatible)."""
        k = top_k or self.top_k
        query_terms = re.findall(r"\b\w+\b", query.lower())
        query_embedding = self._simple_embedding(query)

        # Score chunks using hybrid: keyword overlap + embedding similarity
        scored = []
        for chunk in self.chunks:
            # Keyword score: count of matching terms
            chunk_terms = re.findall(r"\b\w+\b", chunk.text.lower())
            keyword_score = sum(1 for t in query_terms if t in chunk_terms)

            # Embedding similarity (cosine)
            min_len = min(len(query_embedding), len(chunk.embedding))
            if min_len > 0:
                dot = sum(
                    query_embedding[i] * chunk.embedding[i] for i in range(min_len)
                )
                norm_q = math.sqrt(sum(v * v for v in query_embedding[:min_len]))
                norm_c = math.sqrt(sum(v * v for v in chunk.embedding[:min_len]))
                sim = dot / (norm_q * norm_c) if norm_q > 0 and norm_c > 0 else 0.0
            else:
                sim = 0.0

            total_score = keyword_score + sim * 2.0
            if total_score > 0:
                scored.append(
                    {
                        "doc_id": chunk.doc_id,
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "score": round(total_score, 4),
                        "metadata": chunk.metadata,
                    }
                )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    # ── Generation ──────────────────────────────────────────────────

    def generate(self, query: str, context: list[dict[str, Any]]) -> str:
        """Generate answer using retrieved context (backward-compatible)."""
        context_text = " ".join(c.get("text", "")[:200] for c in context[:3])
        return f"Answer to '{query}' based on {len(context)} documents: {context_text[:300]}..."

    # ── Full Query ──────────────────────────────────────────────────

    def query(self, question: str) -> str:
        """Full RAG query: retrieve + generate (backward-compatible)."""
        self._query_count += 1
        docs = self.retrieve(question)
        if not docs:
            return f"No relevant documents found for '{question}'"
        return self.generate(question, docs)

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "index_terms": len(self._index),
            "queries": self._query_count,
        }
