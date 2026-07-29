"""Agent Memory Optimization — vector compression (v11.3.0).

Closes the roadmap item "Implement Agent Memory Optimization (Vector
compression)" from v10.17.0.

Provides two cooperating pieces:

1. :class:`HashingVectorizer` — dependency-free text → dense vector
   projection (signed hashing trick + L2 normalisation). Produces
   deterministic vectors without a fitted vocabulary, which is what the
   agent memory needs (entries arrive in streaming fashion).

2. :class:`VectorCompressor` — lossy storage compressor for dense
   vectors: Johnson–Lindenstrauss random projection (deterministic,
   Achlioptas ±1 matrix) down to ``target_dim`` followed by per-vector
   affine scalar quantisation to uint8. Compressed vectors keep cosine
   geometry well enough for similarity recall while costing
   ``target_dim + 16`` bytes instead of ``source_dim * 8`` bytes.

Typical saving for the default 512 → 64 path: 4096 B → 80 B (~51x),
with top-1 recall preserved on memory-sized corpora (see tests).
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "AdaptiveTuner",
    "CompressedVector",
    "HashingVectorizer",
    "VectorCompressor",
    "ranking_overlap",
]


# ── Compressed vector container ─────────────────────────────────────────


@dataclass
class CompressedVector:
    """Quantised projection of a dense vector.

    ``payload`` holds ``dims`` uint8 values; the original floating range
    of the *projected* vector was ``[vmin, vmax]`` (per-vector affine
    scale). ``source_dim`` is kept for diagnostics only.
    """

    dims: int
    source_dim: int
    vmin: float
    vmax: float
    payload: bytes

    def byte_size(self) -> int:
        """Actual storage footprint in bytes (payload + 2 f64 + 2 i32)."""
        return len(self.payload) + 2 * 8 + 2 * 4

    def to_dict(self) -> dict[str, Any]:
        return {
            "dims": self.dims,
            "source_dim": self.source_dim,
            "vmin": self.vmin,
            "vmax": self.vmax,
            "payload_hex": self.payload.hex(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CompressedVector:
        return CompressedVector(
            dims=int(data["dims"]),
            source_dim=int(data["source_dim"]),
            vmin=float(data["vmin"]),
            vmax=float(data["vmax"]),
            payload=bytes.fromhex(data["payload_hex"]),
        )


# ── Text vectorisation ──────────────────────────────────────────────────


class HashingVectorizer:
    """Deterministic token-hashing vectoriser (signed hashing trick).

    Every token lands in bucket ``md5(token) % dim`` with sign
    ``±1``; the result is L2-normalised. No vocabulary, no fitting —
    stable across processes, which memory persistence relies on.
    """

    def __init__(self, dim: int = 512) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def vectorize(self, text: str) -> np.ndarray:
        """Map arbitrary text to an L2-normalised ``dim``-vector."""
        vec = np.zeros(self.dim, dtype=np.float64)
        tokens = text.lower().split()
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[bucket] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec


# ── Compression ─────────────────────────────────────────────────────────


class VectorCompressor:
    """Random-projection + scalar-quantisation vector compressor.

    Args:
        target_dim: dimensionality of the compressed space.
        seed: seed for the deterministic projection matrix.
    """

    def __init__(self, target_dim: int = 64, seed: int = 42) -> None:
        if target_dim <= 0:
            raise ValueError("target_dim must be positive")
        self.target_dim = target_dim
        self.seed = seed
        self._projection: np.ndarray | None = None
        self._source_dim: int | None = None

    # -- projection matrix ------------------------------------------------

    def fit(self, source_dim: int) -> None:
        """Build the deterministic Achlioptas projection for ``source_dim``.

        Entries are ±1 with probability 1/2, scaled by
        ``1/sqrt(target_dim)`` — a classic JL embedding that provably
        preserves pairwise distances up to small distortion.
        """
        if source_dim <= 0:
            raise ValueError("source_dim must be positive")
        rng = np.random.default_rng(self.seed)
        matrix = rng.choice(
            np.array([-1.0, 1.0]),
            size=(self.target_dim, source_dim),
        )
        self._projection = matrix / math.sqrt(self.target_dim)
        self._source_dim = source_dim

    @property
    def source_dim(self) -> int | None:
        return self._source_dim

    def _ensure_fit(self, source_dim: int) -> None:
        if self._projection is None or self._source_dim != source_dim:
            self.fit(source_dim)

    # -- (de)compression ---------------------------------------------------

    def project(self, vector: np.ndarray) -> np.ndarray:
        """Project a dense vector into compressed (floating) space."""
        vec = np.asarray(vector, dtype=np.float64).ravel()
        self._ensure_fit(vec.shape[0])
        assert self._projection is not None  # for type checkers
        return self._projection @ vec

    def compress(self, vector: np.ndarray) -> CompressedVector:
        """Project + quantise a dense vector into a CompressedVector."""
        projected = self.project(vector)
        vmin = float(projected.min())
        vmax = float(projected.max())
        span = vmax - vmin
        if span <= 1e-12:
            payload = np.zeros(self.target_dim, dtype=np.uint8)
        else:
            payload = np.round((projected - vmin) * (255.0 / span)).astype(np.uint8)
        return CompressedVector(
            dims=self.target_dim,
            source_dim=int(np.asarray(vector).size),
            vmin=vmin,
            vmax=vmax,
            payload=payload.tobytes(),
        )

    def decompress(self, compressed: CompressedVector) -> np.ndarray:
        """Dequantise back into the compressed (floating) space.

        Note: the random projection itself is intentionally kept — the
        compressed space is where similarity is computed (JL geometry
        preservation); round-tripping to the original space is neither
        possible nor needed.
        """
        if compressed.dims != self.target_dim:
            raise ValueError(f"CompressedVector dims {compressed.dims} != compressor target_dim {self.target_dim}")
        raw = np.frombuffer(compressed.payload, dtype=np.uint8).astype(np.float64)
        span = compressed.vmax - compressed.vmin
        return raw * (span / 255.0) + compressed.vmin

    def cosine_similarity(self, a: CompressedVector, b: CompressedVector) -> float:
        """Cosine similarity between two compressed vectors."""
        va = self.decompress(a)
        vb = self.decompress(b)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom <= 1e-12:
            return 0.0
        return float(np.dot(va, vb) / denom)

    # -- reporting -----------------------------------------------------------

    def storage_report(self, source_dim: int | None = None) -> dict[str, Any]:
        """Byte-level compression ratio for the current configuration."""
        src = source_dim or self._source_dim or 0
        original_bytes = src * 8  # float64
        compressed_bytes = self.target_dim + 16  # uint8 payload + vmin/vmax f64
        return {
            "source_dim": src,
            "target_dim": self.target_dim,
            "original_bytes": original_bytes,
            "compressed_bytes": compressed_bytes,
            "ratio": round(original_bytes / compressed_bytes, 2) if compressed_bytes else 0.0,
        }


# Convenience binary pack/unpack — used by persistence layers.
_VECTOR_HEADER = struct.Struct("<II")  # dims, source_dim
_SCALE = struct.Struct("<dd")  # vmin, vmax


def pack_compressed(cv: CompressedVector) -> bytes:
    """Serialise a CompressedVector to a self-describing blob."""
    return _VECTOR_HEADER.pack(cv.dims, cv.source_dim) + _SCALE.pack(cv.vmin, cv.vmax) + cv.payload


def unpack_compressed(blob: bytes) -> CompressedVector:
    """Inverse of :func:`pack_compressed`."""
    header = _VECTOR_HEADER.size
    dims, source_dim = _VECTOR_HEADER.unpack(blob[:header])
    vmin, vmax = _SCALE.unpack(blob[header : header + _SCALE.size])
    payload = blob[header + _SCALE.size :]
    if len(payload) != dims:
        raise ValueError(f"payload length {len(payload)} != dims {dims}")
    return CompressedVector(dims=dims, source_dim=source_dim, vmin=vmin, vmax=vmax, payload=payload)


# ── Adaptive dimension tuning (v11.5.0) ───────────────────────────────


def ranking_overlap(dense_ranking: list[str], compressed_ranking: list[str], k: int) -> float:
    """Fraction of top-k agreement between two rankings over the same ids.

    Edge cases: ``k <= 0`` or two empty rankings → 1.0 (vacuous agreement);
    exactly one empty ranking → 0.0.
    """
    if k <= 0:
        return 1.0
    dense_top = dense_ranking[:k]
    comp_top = compressed_ranking[:k]
    if not dense_top and not comp_top:
        return 1.0
    if not dense_top or not comp_top:
        return 0.0
    return len(set(comp_top) & set(dense_top)) / float(k)


class AdaptiveTuner:
    """Pick the smallest compression dim that preserves recall rankings.

    Probes a handful of entries as pseudo-queries: for each candidate dim,
    entry rankings by dense cosine and by compressed cosine are compared
    via top-k :func:`ranking_overlap`; a dim's score is the mean overlap
    across probes. The smallest dim scoring >= ``min_overlap`` wins; if no
    dim qualifies, the largest candidate is returned (quality beats
    savings).
    """

    DEFAULT_DIMS = (16, 32, 64, 128)

    def __init__(
        self,
        vectorizer: HashingVectorizer,
        dims: tuple[int, ...] | list[int] | None = None,
        min_overlap: float = 0.8,
        top_k: int = 5,
        seed: int = 42,
    ) -> None:
        if not 0.0 <= min_overlap <= 1.0:
            raise ValueError("min_overlap must be in [0.0, 1.0]")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        self.vectorizer = vectorizer
        self.dims = tuple(sorted({int(d) for d in (dims or self.DEFAULT_DIMS)}))
        if not self.dims or self.dims[0] <= 0:
            raise ValueError("dims must be positive")
        self.min_overlap = float(min_overlap)
        self.top_k = int(top_k)
        self.seed = int(seed)

    @staticmethod
    def _dense_cosine(a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom <= 1e-12:
            return 0.0
        return float(np.dot(a, b) / denom)

    def evaluate(self, entries: dict[str, str], probes: int = 8) -> dict[int, float]:
        """Mean top-k overlap per candidate dim.

        Args:
            entries: memory_id -> text to vectorise.
            probes: max number of pseudo-queries (evenly spaced over ids).
        """
        ids = sorted(entries)
        if len(ids) < 2:
            return dict.fromkeys(self.dims, 1.0)

        dense = {mid: self.vectorizer.vectorize(entries[mid]) for mid in ids}
        k = min(self.top_k, len(ids))
        step = max(1, len(ids) // max(1, probes))
        probe_ids = ids[::step][:probes] or [ids[0]]
        dense_rankings = {
            pid: sorted(ids, key=lambda m: -self._dense_cosine(dense[pid], dense[m])) for pid in probe_ids
        }

        scores: dict[int, float] = {}
        for dim in self.dims:
            compressor = VectorCompressor(target_dim=dim, seed=self.seed)
            compressor.fit(self.vectorizer.dim)
            compressed = {mid: compressor.compress(dense[mid]) for mid in ids}
            total = 0.0
            for pid in probe_ids:
                comp_ranking = sorted(
                    ids,
                    key=lambda m: -compressor.cosine_similarity(compressed[pid], compressed[m]),
                )
                total += ranking_overlap(dense_rankings[pid], comp_ranking, k)
            scores[dim] = round(total / len(probe_ids), 4)
        return scores

    def select(self, entries: dict[str, str], probes: int = 8) -> dict[str, Any]:
        """Evaluate all candidate dims and pick the smallest qualifying one."""
        scores = self.evaluate(entries, probes=probes)
        selected = next((d for d in self.dims if scores[d] >= self.min_overlap), self.dims[-1])
        return {
            "selected_dim": selected,
            "scores": {str(d): scores[d] for d in self.dims},
            "min_overlap": self.min_overlap,
            "top_k": self.top_k,
            "probes_used": min(max(1, len(entries)), max(1, probes)),
            "entries": len(entries),
        }
