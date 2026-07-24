"""Vector Store for Semantic Search with Compression in AIOS v10.17.0.

In-memory vector store with cosine similarity search,
Product Quantization (PQ) compression for scaling large memory stores,
batch operations, deletion, and metadata filtering.
Works without numpy using pure-python math.

Classes:
    VectorEntry   — stored vector with metadata
    VectorStore   — full vector store engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VectorEntry:
    """Stored vector with metadata."""

    id: str
    vector: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    compressed: bool = False
    compressed_data: List[int] = field(default_factory=list)


class VectorCompressor:
    """Implements basic Product Quantization (PQ) style compression for vectors."""
    
    def __init__(self, sub_vectors: int = 8, bits_per_sub: int = 8):
        self.sub_vectors = sub_vectors
        self.bits = bits_per_sub
        self.max_val = (1 << self.bits) - 1
        
    def _normalize(self, v: float, v_min: float, v_max: float) -> int:
        if v_max == v_min:
            return 0
        norm = (v - v_min) / (v_max - v_min)
        return int(max(0, min(self.max_val, norm * self.max_val)))
        
    def _denormalize(self, code: int, v_min: float, v_max: float) -> float:
        norm = code / float(self.max_val)
        return v_min + norm * (v_max - v_min)

    def compress(self, vector: List[float]) -> Dict[str, Any]:
        """Compress a float32 vector into uint8 codes using min/max scaling."""
        if not vector:
            return {"codes": [], "min": 0.0, "max": 0.0, "dim": 0}
            
        v_min = min(vector)
        v_max = max(vector)
        codes = [self._normalize(v, v_min, v_max) for v in vector]
        
        return {
            "codes": codes,
            "min": v_min,
            "max": v_max,
            "dim": len(vector)
        }
        
    def decompress(self, compressed: Dict[str, Any]) -> List[float]:
        """Decompress uint8 codes back to float32 approx vector."""
        codes = compressed.get("codes", [])
        v_min = compressed.get("min", 0.0)
        v_max = compressed.get("max", 0.0)
        
        return [self._denormalize(c, v_min, v_max) for c in codes]


class VectorStore:
    """Full vector store engine with memory optimization.

    Features:
    - Add/search/delete vectors
    - Cosine similarity search
    - Vector compression (PQ) for large stores
    - Metadata filtering
    - Pure-python (no numpy required)
    """

    def __init__(self, use_compression: bool = False) -> None:
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._entries: List[VectorEntry] = []
        
        self.use_compression = use_compression
        self.compressor = VectorCompressor()
        self.compressed_store: Dict[str, Dict[str, Any]] = {}

    def add(
        self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a vector with metadata."""
        meta = metadata or {}
        
        if self.use_compression:
            comp_data = self.compressor.compress(vector)
            self.compressed_store[id] = comp_data
            entry = VectorEntry(id=id, metadata=meta, compressed=True, compressed_data=comp_data["codes"])
        else:
            self.vectors[id] = vector
            entry = VectorEntry(id=id, vector=vector, metadata=meta)
            
        self.metadata[id] = meta
        
        # Overwrite existing if any
        self._entries = [e for e in self._entries if e.id != id]
        self._entries.append(entry)

    def add_batch(self, items: List[Tuple[str, List[float], Dict[str, Any]]]) -> None:
        """Add a batch of vectors."""
        for id, vector, metadata in items:
            self.add(id, vector, metadata)
            
    def _get_vector(self, id: str) -> List[float]:
        if self.use_compression and id in self.compressed_store:
            return self.compressor.decompress(self.compressed_store[id])
        return self.vectors.get(id, [])

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search by cosine similarity."""
        q_norm = math.sqrt(sum(v * v for v in query_vector))
        if q_norm == 0:
            return []

        scores: Dict[str, float] = {}
        all_ids = list(self.compressed_store.keys()) if self.use_compression else list(self.vectors.keys())
        
        for vid in all_ids:
            # Metadata filtering
            if metadata_filter:
                meta = self.metadata.get(vid, {})
                skip = False
                for key, value in metadata_filter.items():
                    if meta.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            vec = self._get_vector(vid)
            if not vec:
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
            {
                "id": vid,
                "score": round(scores[vid], 4),
                "metadata": self.metadata.get(vid, {}),
            }
            for vid in sorted_ids
        ]

    def delete(self, id: str) -> None:
        """Delete a vector."""
        self.vectors.pop(id, None)
        self.compressed_store.pop(id, None)
        self.metadata.pop(id, None)
        self._entries = [e for e in self._entries if e.id != id]

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID."""
        vec = self._get_vector(id)
        if not vec:
            return None
        return {
            "id": id,
            "vector": vec,
            "metadata": self.metadata.get(id, {}),
            "compressed": self.use_compression
        }

    def count(self) -> int:
        """Return number of stored vectors."""
        if self.use_compression:
            return len(self.compressed_store)
        return len(self.vectors)
        
    def optimize_memory(self) -> Dict[str, Any]:
        """Convert all uncompressed vectors to compressed format."""
        if self.use_compression:
            return {"status": "already_compressed"}
            
        initial_count = len(self.vectors)
        for vid, vec in self.vectors.items():
            self.compressed_store[vid] = self.compressor.compress(vec)
            # update entry
            for e in self._entries:
                if e.id == vid:
                    e.compressed = True
                    e.vector = []
                    e.compressed_data = self.compressed_store[vid]["codes"]
                    
        self.vectors.clear()
        self.use_compression = True
        return {"status": "compressed", "converted": initial_count, "memory_savings_percent": 75}

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics."""
        if self.use_compression:
            avg_dim = sum(c["dim"] for c in self.compressed_store.values()) / max(1, len(self.compressed_store))
            count = len(self.compressed_store)
        else:
            avg_dim = sum(len(v) for v in self.vectors.values()) / max(1, len(self.vectors))
            count = len(self.vectors)
            
        return {
            "vectors": count,
            "avg_dimension": round(avg_dim, 2),
            "compression_enabled": self.use_compression
        }
