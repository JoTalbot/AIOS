"""Agent Memory Deduplication (v11.4.0).

Near-duplicate detection over the compressed memory index built by
``aios_core.memory_compression``. Pairs of memories whose compressed
cosine similarity exceeds a threshold are clustered via union-find and
merged into a single representative entry.

Complexity: pairwise comparison is O(n²) over the scanned pool, which is
acceptable at agent-memory scale (10²–10⁴ entries, each an 80-byte
compressed vector). Groups are computed from compressed signatures only,
so detection costs no extra storage beyond the existing index.

Merge policy (applied by ``AgentMemorySystem.deduplicate``): the
strongest entry in a group is the representative; it absorbs the access
counts and the best confidence of the absorbed members.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .memory_compression import CompressedVector, VectorCompressor

__all__ = ["DEFAULT_TUNING_CANDIDATES", "DuplicateGroup", "MemoryDeduplicator", "tune_dedup_threshold"]

#: Candidate thresholds scanned by tune_dedup_threshold() when the caller
#: does not provide its own list.
DEFAULT_TUNING_CANDIDATES = (0.80, 0.85, 0.90, 0.92, 0.95, 0.98)


@dataclass
class DuplicateGroup:
    """A cluster of near-duplicate memories (>= 2 members)."""

    representative_id: str
    member_ids: list[str]
    avg_similarity: float

    @property
    def size(self) -> int:
        """Number of memories in the group."""
        return len(self.member_ids)

    def absorbed_ids(self) -> list[str]:
        """Members that will be merged into the representative."""
        return [mid for mid in self.member_ids if mid != self.representative_id]

    def to_dict(self) -> dict[str, Any]:
        """Serialize group for JSON APIs / reports."""
        return {
            "representative_id": self.representative_id,
            "member_ids": list(self.member_ids),
            "absorbed_ids": self.absorbed_ids(),
            "size": self.size,
            "avg_similarity": round(self.avg_similarity, 4),
        }


class _UnionFind:
    """Classic disjoint-set with union by rank (deterministic iteration order)."""

    def __init__(self, items: list[str]) -> None:
        self._parent = {x: x for x in items}
        self._rank = dict.fromkeys(items, 0)

    def find(self, x: str) -> str:
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        # Path compression
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


class MemoryDeduplicator:
    """Detects near-duplicate memories from their compressed signatures."""

    DEFAULT_THRESHOLD = 0.92

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold must be in (0.0, 1.0]")
        self.threshold = float(threshold)

    def find_groups(
        self,
        vectors: dict[str, CompressedVector],
        compressor: VectorCompressor,
        score: dict[str, float] | None = None,
    ) -> list[DuplicateGroup]:
        """Cluster memory ids whose pairwise cosine similarity >= threshold.

        Args:
            vectors: memory_id -> CompressedVector index (e.g. from
                AgentMemorySystem.optimize_storage()).
            compressor: fitted VectorCompressor used for cosine similarity.
            score: optional memory_id -> strength used to pick each group's
                representative (highest score wins; ties break on id).

        Returns:
            DuplicateGroups with >= 2 members, sorted by size (desc) then
            representative id (asc) for deterministic output.
        """
        ids = sorted(vectors)
        if len(ids) < 2:
            return []

        uf = _UnionFind(ids)
        pair_sims: dict[tuple[str, str], float] = {}
        for i, a in enumerate(ids):
            va = vectors[a]
            for b in ids[i + 1 :]:
                sim = compressor.cosine_similarity(va, vectors[b])
                if sim >= self.threshold:
                    uf.union(a, b)
                    pair_sims[(a, b)] = sim

        components: dict[str, list[str]] = {}
        for mid in ids:
            components.setdefault(uf.find(mid), []).append(mid)

        groups: list[DuplicateGroup] = []
        for members in components.values():
            if len(members) < 2:
                continue
            members.sort()
            sims = [
                pair_sims.get((min(a, b), max(a, b)), 0.0) for idx, a in enumerate(members) for b in members[idx + 1 :]
            ]
            # Only count pairs that actually met the threshold (a group is a
            # connected component; not every internal pair needs to qualify).
            linked = [s for s in sims if s > 0.0] or [1.0]
            avg_sim = sum(linked) / len(linked)

            representative = max(members, key=lambda m: (score.get(m, 0.0), m)) if score else members[0]
            groups.append(
                DuplicateGroup(
                    representative_id=representative,
                    member_ids=members,
                    avg_similarity=avg_sim,
                )
            )

        groups.sort(key=lambda g: (-g.size, g.representative_id))
        return groups


def tune_dedup_threshold(
    vectors: dict[str, CompressedVector],
    compressor: VectorCompressor,
    score: dict[str, float] | None = None,
    candidates: list[float] | None = None,
) -> dict[str, Any]:
    """Scan candidate similarity thresholds and recommend the best one
    (v11.9.0).

    The full union-find clustering runs once per candidate; every run is
    scored as ``duplicates * avg_similarity`` — merge as many duplicates
    as possible, but weight the merge by intra-group confidence. Ties
    break toward the HIGHER threshold (merging is irreversible, so equal
    quality prefers the more conservative cut-off). When no candidate
    finds any duplicates, the DEFAULT_THRESHOLD is kept.

    Args:
        vectors: memory_id -> CompressedVector index.
        compressor: fitted compressor used for cosine similarity.
        score: optional memory_id -> strength for representative choice.
        candidates: thresholds to scan (defaults to
            DEFAULT_TUNING_CANDIDATES); each must be in (0.0, 1.0].

    Returns:
        Report dict: recommended_threshold, per-candidate stats,
        duplicates found at the recommendation and a human rationale.
    """
    raw = list(DEFAULT_TUNING_CANDIDATES if candidates is None else candidates)
    if not raw:
        raise ValueError("candidates must be a non-empty list of thresholds")
    validated: list[float] = []
    for cand in raw:
        value = float(cand)
        if not 0.0 < value <= 1.0:
            raise ValueError(f"candidate threshold {cand!r} must be in (0.0, 1.0]")
        validated.append(value)
    thresholds = sorted(set(validated))

    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        groups = MemoryDeduplicator(threshold=threshold).find_groups(vectors, compressor, score=score)
        duplicates = sum(g.size - 1 for g in groups)
        avg_sim = sum(g.avg_similarity for g in groups) / len(groups) if groups else 0.0
        rows.append(
            {
                "threshold": threshold,
                "groups": len(groups),
                "duplicates": duplicates,
                "avg_similarity": round(avg_sim, 4),
                "score": round(duplicates * avg_sim, 6),
            }
        )

    productive = [row for row in rows if row["duplicates"] > 0]
    if not productive:
        recommended = MemoryDeduplicator.DEFAULT_THRESHOLD
        duplicates_found = 0
        rationale = "no duplicates at any candidate; keeping the default threshold"
    else:
        best = max(productive, key=lambda row: (row["score"], row["threshold"]))
        recommended = best["threshold"]
        duplicates_found = best["duplicates"]
        rationale = (
            f"best merge score {best['score']} at threshold {recommended} "
            f"({best['duplicates']} duplicates in {best['groups']} groups, "
            f"avg similarity {best['avg_similarity']})"
        )

    return {
        "recommended_threshold": recommended,
        "default_threshold": MemoryDeduplicator.DEFAULT_THRESHOLD,
        "signatures_scanned": len(vectors),
        "duplicates_found": duplicates_found,
        "rationale": rationale,
        "candidates": rows,
    }
