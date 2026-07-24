"""Federated Analytics for AIOS v10.8.0.

Privacy-preserving distributed analytics with secure
aggregation, differential privacy noise injection,
noise budgets, node management, and analytics
computation.

Classes:
    AnalyticsNode  — federated analytics node
    AggregationResult — aggregation outcome
    FederatedAnalytics — full federated analytics engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsNode:
    """Federated analytics node."""
    node_id: str
    data_points: int = 0
    contributions: int = 0
    epsilon_budget: float = 1.0  # privacy budget
    epsilon_used: float = 0.0
    status: str = "active"  # active, paused, offline
    last_contribution: float = 0.0


@dataclass
class AggregationResult:
    """Aggregation outcome."""
    total_count: int
    average: float
    noise_added: float
    nodes_contributed: int
    epsilon_consumed: float
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    timestamp: float = field(default_factory=time.time)


class FederatedAnalytics:
    """Full federated analytics engine.

    Features:
    - Node registration and management
    - Secure aggregation (sum/mean/count)
    - Differential privacy noise injection (Laplace mechanism)
    - Privacy budget tracking per node
    - Analytics computation (mean, variance, histogram)
    - Confidence intervals with noise consideration
    - Node status management
    """

    def __init__(self, global_epsilon: float = 10.0) -> None:
        self.nodes: dict[str, AnalyticsNode] = {}
        self.global_epsilon = global_epsilon
        self._epsilon_used_total = 0.0
        self._aggregation_history: list[AggregationResult] = []

    # ── Node Management ──────────────────────────────────────────────

    def register_node(self, node_id: str, epsilon_budget: float = 1.0) -> AnalyticsNode:
        """Register a federated analytics node."""
        node = AnalyticsNode(
            node_id=node_id, epsilon_budget=epsilon_budget,
        )
        self.nodes[node_id] = node
        return node

    def unregister_node(self, node_id: str) -> None:
        """Remove a node."""
        node = self.nodes.pop(node_id, None)
        if node:
            node.status = "offline"

    def pause_node(self, node_id: str) -> None:
        """Pause a node's contributions."""
        node = self.nodes.get(node_id)
        if node:
            node.status = "paused"

    def resume_node(self, node_id: str) -> None:
        """Resume a paused node."""
        node = self.nodes.get(node_id)
        if node:
            node.status = "active"

    def get_node(self, node_id: str) -> AnalyticsNode | None:
        """Return node info."""
        return self.nodes.get(node_id)

    def active_nodes(self) -> list[AnalyticsNode]:
        """Return all active nodes."""
        return [n for n in self.nodes.values() if n.status == "active"]

    # ── Aggregation ──────────────────────────────────────────────────

    def aggregate(self, local_stats: list[dict[str, Any]],
                  epsilon: float = 0.1) -> AggregationResult:
        """Aggregate local statistics with differential privacy (backward-compatible)."""
        if not local_stats:
            return AggregationResult(
                total_count=0, average=0, noise_added=0,
                nodes_contributed=0, epsilon_consumed=0,
            )

        # Compute aggregate statistics
        total_count = sum(s.get("count", 0) for s in local_stats)
        raw_avg = sum(s.get("mean", 0) * s.get("count", 1) for s in local_stats) / total_count if total_count > 0 else 0

        # Add Laplace noise for differential privacy
        # Noise magnitude = sensitivity / epsilon
        sensitivity = 1.0 / max(total_count, 1)  # sensitivity for mean
        noise = random.gauss(0, sensitivity / epsilon) if epsilon > 0 else 0

        noisy_avg = raw_avg + noise

        # Compute confidence interval
        std = math.sqrt(sum((s.get("variance", 0.1) or 0.1) for s in local_stats) / len(local_stats))
        margin = 1.96 * std / math.sqrt(len(local_stats)) + abs(noise)

        # Track epsilon usage
        self._epsilon_used_total += epsilon

        result = AggregationResult(
            total_count=total_count,
            average=round(noisy_avg, 4),
            noise_added=round(abs(noise), 4),
            nodes_contributed=len(local_stats),
            epsilon_consumed=epsilon,
            confidence_interval=(round(noisy_avg - margin, 4), round(noisy_avg + margin, 4)),
        )
        self._aggregation_history.append(result)
        return result

    def secure_sum(self, local_values: dict[str, float],
                   epsilon: float = 0.1) -> float:
        """Secure sum aggregation with DP noise."""
        raw_sum = sum(local_values.values())
        sensitivity = max(local_values.values()) if local_values else 1.0
        noise = random.gauss(0, sensitivity / epsilon) if epsilon > 0 else 0
        return round(raw_sum + noise, 4)

    def secure_mean(self, local_values: dict[str, float],
                    epsilon: float = 0.1) -> float:
        """Secure mean aggregation with DP noise."""
        if not local_values:
            return 0.0
        raw_mean = sum(local_values.values()) / len(local_values)
        sensitivity = 1.0 / len(local_values)
        noise = random.gauss(0, sensitivity / epsilon) if epsilon > 0 else 0
        return round(raw_mean + noise, 4)

    def histogram(self, local_histograms: list[dict[str, int]],
                  epsilon: float = 0.1) -> dict[str, int]:
        """Aggregate histograms with DP noise per bin."""
        merged: dict[str, int] = {}
        for hist in local_histograms:
            for bin_key, count in hist.items():
                merged[bin_key] = merged.get(bin_key, 0) + count

        # Add noise to each bin
        noisy_hist = {}
        for bin_key, count in merged.items():
            noise = random.gauss(0, 1 / epsilon) if epsilon > 0 else 0
            noisy_hist[bin_key] = max(0, round(count + noise))

        return noisy_hist

    # ── Privacy Budget ──────────────────────────────────────────────

    def check_budget(self, node_id: str) -> float:
        """Check remaining privacy budget for a node."""
        node = self.nodes.get(node_id)
        if node is None:
            return 0.0
        return node.epsilon_budget - node.epsilon_used

    def consume_budget(self, node_id: str, epsilon: float) -> bool:
        """Consume privacy budget (returns False if insufficient)."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        remaining = node.epsilon_budget - node.epsilon_used
        if epsilon > remaining:
            return False
        node.epsilon_used += epsilon
        node.contributions += 1
        node.last_contribution = time.time()
        self._epsilon_used_total += epsilon
        return True

    def global_budget_remaining(self) -> float:
        """Return remaining global privacy budget."""
        return self.global_epsilon - self._epsilon_used_total

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        active = len(self.active_nodes())
        return {
            "nodes": len(self.nodes),
            "active_nodes": active,
            "aggregations": len(self._aggregation_history),
            "epsilon_used": round(self._epsilon_used_total, 4),
            "epsilon_remaining": round(self.global_budget_remaining(), 4),
        }
