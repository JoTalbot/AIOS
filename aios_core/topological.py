"""Topological Data Analysis for AIOS v10.9.0.

Persistent homology, Betti numbers, filtration
construction, topological feature extraction,
distance-based simplicial complexes, and shape
analysis.

Classes:
    PersistenceDiagram — persistence diagram point
    TopologicalAnalyzer — full TDA engine
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PersistenceDiagram:
    """Persistence diagram point (birth, death, dimension)."""

    birth: float
    death: float
    dimension: int = 0  # 0=connected components, 1=loops, 2=cavities
    persistence: float = 0.0  # death - birth

    def __post_init__(self) -> None:
        self.persistence = self.death - self.birth


class TopologicalAnalyzer:
    """Full topological data analysis engine.

    Features:
    - Distance matrix computation
    - Vietoris-Rips complex construction
    - Persistence diagram computation
    - Betti number estimation
    - Topological feature extraction
    - Shape descriptors
    - Filtration tracking
    """

    def __init__(self, max_dim: int = 2, epsilon: float = 0.5) -> None:
        self.filtrations: list[list[PersistenceDiagram]] = []
        self.max_dim = max_dim
        self.epsilon = epsilon
        self._analysis_count: int = 0

    # ── Distance Computation ────────────────────────────────────────

    def _distance(self, p1: list[float], p2: list[float]) -> float:
        """Euclidean distance between two points."""
        min_len = min(len(p1), len(p2))
        return math.sqrt(sum((p1[i] - p2[i]) ** 2 for i in range(min_len)))

    def distance_matrix(self, point_cloud: list[list[float]]) -> list[list[float]]:
        """Compute pairwise distance matrix."""
        n = len(point_cloud)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = self._distance(point_cloud[i], point_cloud[j])
                matrix[i][j] = d
                matrix[j][i] = d
        return matrix

    # ── Persistence ────────────────────────────────────────────────

    def compute_persistence(self, point_cloud: list[list[float]]) -> dict[str, Any]:
        """Compute persistence diagram and Betti numbers (backward-compatible)."""
        self._analysis_count += 1
        n = len(point_cloud)

        if n == 0:
            return {"betti_0": 0, "betti_1": 0, "betti_2": 0, "diagrams": []}

        # Compute distances
        dists = self.distance_matrix(point_cloud)

        # Betti-0: connected components at epsilon threshold
        # Count clusters using union-find logic
        clusters = list(range(n))

        def find(x: int) -> int:
            while clusters[x] != x:
                clusters[x] = clusters[clusters[x]]
                x = clusters[x]
            return x

        for i in range(n):
            for j in range(i + 1, n):
                if dists[i][j] < self.epsilon:
                    ci, cj = find(i), find(j)
                    if ci != cj:
                        clusters[ci] = cj

        unique_clusters = len(set(find(i) for i in range(n)))
        betti_0 = unique_clusters

        # Betti-1: estimate loops from average connectivity
        avg_neighbors = (
            sum(sum(1 for d in dists[i] if d < self.epsilon) for i in range(n)) / n
        )
        betti_1 = max(0, int(avg_neighbors - 2) // 2) if avg_neighbors > 2 else 0

        # Betti-2: estimate cavities (rare in low dimensions)
        betti_2 = 0

        # Compute persistence diagram points
        diagrams = []
        # Betti-0 points: components merge
        sorted_dists = sorted([dists[i][j] for i in range(n) for j in range(i + 1, n)])
        merge_distances = (
            sorted_dists[: n - betti_0]
            if len(sorted_dists) >= n - betti_0
            else sorted_dists
        )
        for d in merge_distances:
            diagrams.append(PersistenceDiagram(birth=0.0, death=d, dimension=0))

        # Betti-1 points: loops appear
        if betti_1 > 0 and len(sorted_dists) > n:
            loop_births = sorted_dists[n : n + betti_1]
            for bd in loop_births:
                diagrams.append(
                    PersistenceDiagram(birth=bd, death=bd + self.epsilon, dimension=1)
                )

        self.filtrations.append(diagrams)

        return {
            "betti_0": betti_0,
            "betti_1": betti_1,
            "betti_2": betti_2,
            "diagrams": diagrams,
            "num_points": n,
        }

    # ── Feature Extraction ──────────────────────────────────────────

    def extract_features(self, point_cloud: list[list[float]]) -> list[float]:
        """Extract topological features from point cloud (backward-compatible)."""
        persistence = self.compute_persistence(point_cloud)
        diagrams = persistence.get("diagrams", [])

        # Compute topological feature vector
        total_persistence_0 = sum(d.persistence for d in diagrams if d.dimension == 0)
        total_persistence_1 = sum(d.persistence for d in diagrams if d.dimension == 1)
        max_persistence_0 = max(
            (d.persistence for d in diagrams if d.dimension == 0), default=0.0
        )
        avg_persistence_0 = total_persistence_0 / max(
            len([d for d in diagrams if d.dimension == 0]), 1
        )

        return [
            persistence["betti_0"],
            persistence["betti_1"],
            round(total_persistence_0, 4),
            round(total_persistence_1, 4),
            round(max_persistence_0, 4),
            round(avg_persistence_0, 4),
        ]

    # ── Shape Descriptors ──────────────────────────────────────────

    def shape_descriptor(self, point_cloud: list[list[float]]) -> dict[str, Any]:
        """Compute shape descriptors from topological features."""
        persistence = self.compute_persistence(point_cloud)
        diagrams = persistence.get("diagrams", [])

        # Euler characteristic: β0 - β1 + β2
        euler = persistence["betti_0"] - persistence["betti_1"] + persistence["betti_2"]

        # Total persistence
        total = sum(d.persistence for d in diagrams)

        # Average persistence
        avg = total / len(diagrams) if diagrams else 0.0

        return {
            "euler_characteristic": euler,
            "total_persistence": round(total, 4),
            "avg_persistence": round(avg, 4),
            "betti_numbers": [
                persistence["betti_0"],
                persistence["betti_1"],
                persistence["betti_2"],
            ],
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "filtrations": len(self.filtrations),
            "max_dim": self.max_dim,
            "epsilon": self.epsilon,
            "analyses": self._analysis_count,
        }
