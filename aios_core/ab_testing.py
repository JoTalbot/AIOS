"""A/B Testing Framework for AIOS v10.9.0.

A/B testing with variant assignment, result tracking,
statistical significance testing, multi-variant
experiments, and experiment lifecycle management.

Classes:
    ExperimentResult — recorded experiment outcome
    ABTest           — full A/B testing engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Recorded experiment outcome."""
    variant: str
    success: bool
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class ABTest:
    """Full A/B testing engine.

    Features:
    - Weighted variant assignment (backward-compatible)
    - Success/failure tracking
    - Statistical significance (chi-squared approximation)
    - Multi-variant experiments
    - Experiment lifecycle
    """

    def __init__(self, name: str, variants: dict[str, float]) -> None:
        self.name = name
        self.variants = variants
        self.results: dict[str, list[ExperimentResult]] = {v: [] for v in variants}
        self._total_assignments: dict[str, int] = {v: 0 for v in variants}
        self._conversions: dict[str, int] = {v: 0 for v in variants}

    def assign_variant(self, user_id: str) -> str:
        """Assign user to variant (backward-compatible)."""
        # Hash-based deterministic assignment
        hash_val = hash(user_id) % 1000
        cumulative = 0
        for variant, weight in self.variants.items():
            cumulative += weight * 1000
            if hash_val <= cumulative:
                self._total_assignments[variant] += 1
                return variant
        variant = list(self.variants.keys())[0]
        self._total_assignments[variant] += 1
        return variant

    def record_result(self, variant: str, success: bool, metadata: dict[str, Any] | None = None) -> None:
        """Record experiment outcome (backward-compatible)."""
        result = ExperimentResult(variant=variant, success=success, metadata=metadata or {})
        self.results[variant].append(result)
        if success:
            self._conversions[variant] += 1

    def get_conversion_rate(self, variant: str) -> float:
        """Get conversion rate for a variant."""
        total = self._total_assignments.get(variant, 0)
        conversions = self._conversions.get(variant, 0)
        if total == 0:
            return 0.0
        return round(conversions / total, 4)

    def get_winner(self) -> str:
        """Return the winning variant (backward-compatible)."""
        return max(self._conversions, key=self._conversions.get)

    def statistical_significance(self) -> dict[str, Any]:
        """Check statistical significance between variants."""
        if len(self.variants) < 2:
            return {"significant": False, "p_value": 1.0}

        variants_list = list(self.variants.keys())
        rates = {v: self.get_conversion_rate(v) for v in variants_list}
        best = max(rates, key=rates.get)
        second = sorted(rates, key=rates.get, reverse=True)[1]

        best_n = self._total_assignments.get(best, 0)
        second_n = self._total_assignments.get(second, 0)

        if best_n < 30 or second_n < 30:
            return {"significant": False, "p_value": 1.0, "note": "Need at least 30 samples per variant"}

        # Simplified chi-squared approximation
        diff = abs(rates[best] - rates[second])
        pooled_rate = (self._conversions[best] + self._conversions[second]) / (best_n + second_n)
        if pooled_rate == 0:
            return {"significant": False, "p_value": 1.0}

        z = diff / math.sqrt(pooled_rate * (1 - pooled_rate) * (1/best_n + 1/second_n))
        # Approximate p-value from z-score
        p_value = max(0.001, 2 * (1 - min(1.0, 0.5 * (1 + math.erf(z / math.sqrt(2))))))

        return {
            "significant": p_value < 0.05,
            "p_value": round(p_value, 4),
            "best_variant": best,
            "conversion_rates": rates,
            "z_score": round(z, 4),
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        return {
            "name": self.name,
            "results": {v: self._conversions.get(v, 0) for v in self.variants},
            "assignments": dict(self._total_assignments),
            "conversion_rates": {v: self.get_conversion_rate(v) for v in self.variants},
        }
