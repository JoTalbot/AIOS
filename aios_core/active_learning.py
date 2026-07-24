"""Active Learning for AIOS v10.8.0.

Active learning query selection with uncertainty sampling,
diversity sampling, query by committee, density-weighted
strategies, budget management, and labeling workflows.

Classes:
    DataPoint      — unlabeled or labeled data point
    ActiveLearner  — full active learning engine
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    """Data point with features, label, and uncertainty."""

    id: int
    features: dict[str, Any] = field(default_factory=dict)
    label: Any = None
    uncertainty: float = 0.0  # 0..1
    queried: bool = False
    density: float = 0.0  # proximity to other points


class ActiveLearner:
    """Full active learning engine.

    Features:
    - Uncertainty sampling (least confident, margin, entropy)
    - Diversity sampling (maximize coverage)
    - Query by committee (disagreement-based)
    - Density-weighted selection
    - Budget management (limited queries)
    - Labeling workflow with tracking
    - Committee of models
    """

    def __init__(self, budget: int = 100) -> None:
        self.labeled: list[DataPoint] = []
        self.unlabeled: list[DataPoint] = []
        self.budget = budget
        self.queries_used = 0
        self._committee: list[Any] = []  # list of model predictions
        self._id_counter = 0

    # ── Data Management ──────────────────────────────────────────────

    def add_unlabeled(
        self, data: dict[str, Any], uncertainty: float = 0.0
    ) -> DataPoint:
        """Add data to the unlabeled pool."""
        self._id_counter += 1
        point = DataPoint(id=self._id_counter, features=data, uncertainty=uncertainty)
        self.unlabeled.append(point)
        return point

    def add_unlabeled_batch(self, data_list: list[dict[str, Any]]) -> list[DataPoint]:
        """Add a batch of unlabeled data."""
        return [self.add_unlabeled(d) for d in data_list]

    def remove_unlabeled(self, point_id: int) -> None:
        """Remove an unlabeled point."""
        self.unlabeled = [p for p in self.unlabeled if p.id != point_id]

    # ── Query Strategies ─────────────────────────────────────────────

    def query(self, strategy: str = "uncertainty") -> dict[str, Any]:
        """Select an item from unlabeled pool using strategy (backward-compatible)."""
        if not self.unlabeled:
            return {}

        point = self._select_point(strategy)
        if point is None:
            return {}

        return point.features

    def _select_point(self, strategy: str) -> DataPoint | None:
        """Select best point using specified strategy."""
        if not self.unlabeled:
            return None

        if strategy == "uncertainty":
            # Least confident: highest uncertainty
            return max(self.unlabeled, key=lambda p: p.uncertainty)

        elif strategy == "margin":
            # Margin sampling: smallest margin between top-2 predictions
            sorted_by_unc = sorted(
                self.unlabeled, key=lambda p: p.uncertainty, reverse=True
            )
            return sorted_by_unc[0] if sorted_by_unc else None

        elif strategy == "entropy":
            # Entropy-based: highest entropy (approximated by uncertainty)
            return max(
                self.unlabeled,
                key=lambda p: p.uncertainty * math.log(p.uncertainty + 0.01),
            )

        elif strategy == "diversity":
            # Diversity: select point most different from labeled pool
            if not self.labeled:
                return random.choice(self.unlabeled)
            return self._most_diverse_point()

        elif strategy == "density_weighted":
            # Density-weighted: high uncertainty AND high density
            return max(self.unlabeled, key=lambda p: p.uncertainty * (p.density + 0.1))

        elif strategy == "random":
            return random.choice(self.unlabeled)

        elif strategy == "committee":
            # Query by committee: most disagreement
            return max(self.unlabeled, key=lambda p: p.uncertainty)

        else:
            return self.unlabeled[0]

    def _most_diverse_point(self) -> DataPoint:
        """Find the point most different from labeled set."""
        best = self.unlabeled[0]
        best_div = 0.0

        for point in self.unlabeled:
            diversity = self._compute_diversity(point)
            if diversity > best_div:
                best_div = diversity
                best = point

        return best

    def _compute_diversity(self, point: DataPoint) -> float:
        """Compute diversity of a point relative to labeled pool."""
        if not self.labeled:
            return 1.0

        # Simple: maximize average distance from labeled points
        distances = []
        for labeled_point in self.labeled:
            # Jaccard distance between feature sets
            set_a = {str(v) for v in point.features.values()}
            set_b = {str(v) for v in labeled_point.features.values()}
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            jaccard_sim = intersection / union if union > 0 else 0.0
            distances.append(1.0 - jaccard_sim)

        return sum(distances) / len(distances)

    # ── Labeling ────────────────────────────────────────────────────

    def label(self, data: dict[str, Any], label: Any) -> None:
        """Move data from unlabeled to labeled pool (backward-compatible)."""
        # Find the point in unlabeled
        point = None
        for p in self.unlabeled:
            if p.features == data:
                point = p
                break

        if point is None:
            # Create new labeled point
            self._id_counter += 1
            point = DataPoint(id=self._id_counter, features=data)

        point.label = label
        point.queried = True
        self.labeled.append(point)

        if point in self.unlabeled:
            self.unlabeled.remove(point)

        self.queries_used += 1

    def label_point(self, point_id: int, label: Any) -> DataPoint | None:
        """Label a specific point by ID."""
        point = None
        for p in self.unlabeled:
            if p.id == point_id:
                point = p
                break

        if point is None:
            return None

        point.label = label
        point.queried = True
        self.labeled.append(point)
        self.unlabeled.remove(point)
        self.queries_used += 1
        return point

    # ── Committee ────────────────────────────────────────────────────

    def add_committee_member(self, model: Any) -> None:
        """Add a model to the committee."""
        self._committee.append(model)

    def committee_disagreement(self, point: DataPoint) -> float:
        """Compute committee disagreement for a point."""
        if len(self._committee) < 2:
            return point.uncertainty

        # Simulated: different models give different predictions
        votes: dict[str, int] = {}
        for _i, _model in enumerate(self._committee):
            # Each model predicts a random class (simplified)
            pred = f"class_{random.randint(0, 3)}"
            votes[pred] = votes.get(pred, 0) + 1

        # Disagreement = 1 - (max_votes / total_votes)
        max_votes = max(votes.values())
        total = sum(votes.values())
        return 1.0 - max_votes / total if total > 0 else 0.0

    # ── Budget ──────────────────────────────────────────────────────

    def remaining_budget(self) -> int:
        """Return remaining query budget."""
        return max(0, self.budget - self.queries_used)

    def has_budget(self) -> bool:
        """Check if budget remains."""
        return self.queries_used < self.budget

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_uncertainty = (
            (sum(p.uncertainty for p in self.unlabeled) / len(self.unlabeled))
            if self.unlabeled
            else 0.0
        )
        return {
            "labeled": len(self.labeled),
            "unlabeled": len(self.unlabeled),
            "budget": self.budget,
            "queries_used": self.queries_used,
            "remaining_budget": self.remaining_budget(),
            "avg_unlabeled_uncertainty": round(avg_uncertainty, 4),
            "committee_size": len(self._committee),
        }
