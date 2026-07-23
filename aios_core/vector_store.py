"""Vector Store for Semantic Search in AIOS"""

from typing import Any, Dict, List

import numpy as np


class VectorStore:
    """Simple in-memory vector store with cosine similarity."""

    def __init__(self):
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict] = {}

    def add(self, id: str, vector: List[float], metadata: Dict = None) -> None:
        self.vectors[id] = np.array(vector)
        self.metadata[id] = metadata or {}

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        q = np.array(query_vector)
        scores = {}
        for vid, vec in self.vectors.items():
            sim = np.dot(q, vec) / (np.linalg.norm(q) * np.linalg.norm(vec))
            scores[vid] = float(sim)

        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        return [
            {"id": vid, "score": scores[vid], "metadata": self.metadata[vid]} for vid in sorted_ids
        ]

    def stats(self) -> dict:
        return {"vectors": len(self.vectors)}
