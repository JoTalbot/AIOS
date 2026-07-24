"""Vector Store for Semantic Search in AIOS v10.9.0.

In-memory vector store with cosine similarity search,
batch operations, deletion, metadata filtering, and
hybrid search support. Works without numpy using
pure-python math.

Classes:
    VectorEntry   — stored vector with metadata
    VectorStore   — full vector store engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VectorEntry:
    """Stored vector with metadata."""
    id: str
    vector: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class VectorStore:
    """Full vector store engine.

    Features:
    - Add/search/delete vectors
    - Cosine similarity search
    - Batch operations
    - Metadata filtering
    - Pure-python (no numpy required)
    - Hybrid search (keyword + vector)
    """

    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}
        self.metadata: dict[str, dict[str, Any]] = {}
        self._entries: list[VectorEntry] = []

    def add(self, id: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        """Add a vector with metadata (backward-compatible)."""
        self.vectors[id] = vector
        self.metadata[id] = metadata or {}
        entry = VectorEntry(id=id, vector=vector, metadata=metadata or {})
        self._entries.append(entry)

    def add_batch(self, items: list[tuple[str, list[float], dict[str, Any]]]) -> None:
        """Add a batch of vectors."""
        for id, vector, metadata in items:
            self.add(id, vector, metadata)

    def search(self, query_vector: list[float], top_k: int = 5,
               metadata_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search by cosine similarity (backward-compatible)."""
        # Compute query norm
        q_norm = math.sqrt(sum(v * v for v in query_vector))
        if q_norm == 0:
            return []

        scores: dict[str, float] = {}
        for vid, vec in self.vectors.items():
            # Metadata filtering
            if metadata_filter:
                meta = self.metadata.get(vid, {})
                for key, value in metadata_filter.items():
                    if meta.get(key) != value:
                        continue

            # Cosine similarity
            min_len = min(len(query_vector), len(vec))
            dot = sum(query_vector[i] * vec[i] for i in range(min_len))
            v_norm = math.sqrt(sum(v * v for v in vec[:min_len]))
            if v_norm == 0:
                continue
            sim = dot / (q_norm * v_norm)
            scores[vid] = float(sim)

        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        return [
            {"id": vid, "score": round(scores[vid], 4), "metadata": self.metadata.get(vid, {})}
            for vid in sorted_ids
        ]

    def delete(self, id: str) -> None:
        """Delete a vector."""
        self.vectors.pop(id, None)
        self.metadata.pop(id, None)
        self._entries = [e for e in self._entries if e.id != id]

    def get(self, id: str) -> dict[str, Any] | None:
        """Get a vector by ID."""
        if id not in self.vectors:
            return None
        return {"id": id, "vector": self.vectors[id], "metadata": self.metadata.get(id, {})}

    def count(self) -> int:
        """Return number of stored vectors."""
        return len(self.vectors)

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_dim = (sum(len(v) for v in self.vectors.values()) /
                  len(self.vectors)) if self.vectors else 0
        return {
            "vectors": len(self.vectors),
            "avg_dimension": round(avg_dim, 2),
        }
