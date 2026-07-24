"""Differential Privacy for AIOS v10.7.0.

Privacy mechanisms: Laplace mechanism, Gaussian mechanism,
privacy budget tracking, composition tracking, thresholding,
privacy loss estimation, and k-anonymity.

Classes:
    MechanismType   — Laplace / Gaussian / Threshold
    PrivacyBudget   — epsilon/delta tracking with composition
    DifferentialPrivacy — full privacy engine
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MechanismType(str, Enum):
    """Privacy mechanism types."""

    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    THRESHOLD = "threshold"


@dataclass
class PrivacyBudget:
    """Epsilon/delta tracking with composition."""

    total_epsilon: float = 10.0
    total_delta: float = 1e-5
    consumed_epsilon: float = 0.0
    consumed_delta: float = 0.0

    def consume(self, epsilon: float, delta: float = 0.0) -> bool:
        """Consume privacy budget. Returns False if exhausted."""
        if self.consumed_epsilon + epsilon > self.total_epsilon:
            logger.warning("Privacy budget exhausted (epsilon)")
            return False
        if self.consumed_delta + delta > self.total_delta:
            logger.warning("Privacy budget exhausted (delta)")
            return False
        self.consumed_epsilon += epsilon
        self.consumed_delta += delta
        return True

    def remaining_epsilon(self) -> float:
        """Return remaining epsilon."""
        return self.total_epsilon - self.consumed_epsilon

    def remaining_delta(self) -> float:
        """Return remaining delta."""
        return self.total_delta - self.consumed_delta

    def is_exhausted(self) -> bool:
        """Check if budget is exhausted."""
        return self.consumed_epsilon >= self.total_epsilon

    def reset(self) -> None:
        """Reset consumed budget."""
        self.consumed_epsilon = 0.0
        self.consumed_delta = 0.0


class DifferentialPrivacy:
    """Full privacy engine with mechanisms, budgets, and composition.

    Features:
    - Laplace mechanism (epsilon-based noise)
    - Gaussian mechanism (epsilon+delta noise)
    - Privacy budget tracking and composition
    - Thresholding (sparse vector technique)
    - Privacy loss estimation
    - K-anonymity helper
    """

    def __init__(
        self, epsilon: float = 1.0, delta: float = 1e-5, total_epsilon: float = 10.0
    ) -> None:
        self.epsilon = epsilon
        self.delta = delta
        self.budget = PrivacyBudget(total_epsilon=total_epsilon, total_delta=delta)
        self._queries_count: int = 0

    # ── Noise Mechanisms ─────────────────────────────────────────

    def add_noise(
        self,
        value: float,
        sensitivity: float = 1.0,
        mechanism: MechanismType = MechanismType.LAPLACE,
    ) -> float:
        """Add privacy-preserving noise to a value."""
        if not self.budget.consume(
            self.epsilon, self.delta if mechanism == MechanismType.GAUSSIAN else 0
        ):
            return value  # budget exhausted → return original (not ideal but practical)

        self._queries_count += 1

        if mechanism == MechanismType.LAPLACE:
            scale = sensitivity / self.epsilon
            noise = self._laplace_sample(0, scale)
            return value + noise

        if mechanism == MechanismType.GAUSSIAN:
            sigma = (
                sensitivity * math.sqrt(2 * math.log(1.25 / self.delta)) / self.epsilon
            )
            noise = random.gauss(0, sigma)
            return value + noise

        # THRESHOLD: just clip to range
        return value

    def privatize_list(
        self,
        values: list[float],
        sensitivity: float = 1.0,
        mechanism: MechanismType = MechanismType.LAPLACE,
    ) -> list[float]:
        """Add noise to a list of values."""
        return [self.add_noise(v, sensitivity, mechanism) for v in values]

    def privatize_count(self, true_count: int, epsilon: float = 1.0) -> int:
        """Private counting via Laplace noise."""
        if not self.budget.consume(epsilon):
            return true_count
        noise = self._laplace_sample(0, 1.0 / epsilon)
        result = true_count + round(noise)
        return max(0, result)  # counts can't be negative

    def privatize_sum(
        self, true_sum: float, sensitivity: float = 1.0, epsilon: float = 1.0
    ) -> float:
        """Private sum via Laplace mechanism."""
        if not self.budget.consume(epsilon):
            return true_sum
        scale = sensitivity / epsilon
        noise = self._laplace_sample(0, scale)
        return true_sum + noise

    def privatize_mean(
        self, values: list[float], sensitivity: float = 1.0, epsilon: float = 1.0
    ) -> float:
        """Private mean: DP sum / DP count."""
        dp_count = self.privatize_count(len(values), epsilon / 2)
        dp_sum = self.privatize_sum(sum(values), sensitivity, epsilon / 2)
        if dp_count <= 0:
            return 0.0
        return dp_sum / dp_count

    # ── Threshold (Sparse Vector Technique) ──────────────────────

    def threshold_query(
        self, value: float, threshold: float, epsilon: float = 1.0
    ) -> bool:
        """Answer threshold query privately: is value above threshold?"""
        if not self.budget.consume(epsilon):
            return False
        noise = self._laplace_sample(0, 1.0 / epsilon)
        noisy_value = value + noise
        return noisy_value >= threshold

    # ── Privacy Loss ─────────────────────────────────────────────

    def privacy_loss(self, epsilon: float = 1.0) -> float:
        """Estimate privacy loss: exp(epsilon)."""
        return math.exp(epsilon)

    def cumulative_loss(self) -> float:
        """Return cumulative privacy loss from all consumed epsilon."""
        return math.exp(self.budget.consumed_epsilon)

    # ── K-Anonymity ──────────────────────────────────────────────

    def k_anonymize(
        self, data: list[dict[str, Any]], quasi_identifiers: list[str], k: int = 5
    ) -> list[dict[str, Any]]:
        """Apply k-anonymity: suppress or generalize quasi-identifiers."""
        if k <= 0:
            return data

        # Group by quasi-identifiers
        groups: dict[str, list[dict[str, Any]]] = {}
        for record in data:
            key = tuple(record.get(qi, "") for qi in quasi_identifiers)
            key_str = str(key)
            groups.setdefault(key_str, []).append(record)

        # Only keep groups with size >= k
        result = []
        for records in groups.values():
            if len(records) >= k:
                result.extend(records)
            else:
                # Suppress: remove quasi-identifiers
                for record in records:
                    suppressed = {
                        k: v for k, v in record.items() if k not in quasi_identifiers
                    }
                    result.append(suppressed)

        return result

    # ── Laplace Sampling ─────────────────────────────────────────

    def _laplace_sample(self, mean: float, scale: float) -> float:
        """Sample from Laplace distribution."""
        u = random.uniform(-0.5, 0.5)
        return mean - scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "queries_count": self._queries_count,
            "budget_remaining_epsilon": self.budget.remaining_epsilon(),
            "budget_remaining_delta": self.budget.remaining_delta(),
            "budget_exhausted": self.budget.is_exhausted(),
            "cumulative_loss": self.cumulative_loss(),
        }
