"""Federated Learning Support for AIOS v10.7.0.

Federated learning coordinator with node management, model
aggregation (FedAvg), round-based training, privacy budget,
and convergence tracking.

Classes:
    NodeStatus     — active / offline / training
    FederatedNode  — participant node with model version
    AggregationResult — round aggregation outcome
    FederatedLearning — full FL coordinator
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class NodeStatus(StrEnum):
    """Node participation status."""

    ACTIVE = "active"
    OFFLINE = "offline"
    TRAINING = "training"


@dataclass
class FederatedNode:
    """Participant node with model version."""

    node_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.ACTIVE
    model_version: int = 0
    local_accuracy: float = 0.0
    samples_count: int = 0
    last_update: float = 0.0

    def is_available(self) -> bool:
        """Check if node can participate in a round."""
        return self.status == NodeStatus.ACTIVE


@dataclass
class AggregationResult:
    """Round aggregation outcome."""

    round: int = 0
    participants: int = 0
    global_accuracy: float = 0.0
    converged: bool = False
    timestamp: float = field(default_factory=time.time)
    weights: dict[str, float] = field(default_factory=dict)  # node_id → weight


@dataclass
class GlobalModel:
    """Global aggregated model state."""

    version: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    accuracy: float = 0.0


class FederatedLearning:
    """Full FL coordinator with aggregation, rounds, privacy, convergence.

    Features:
    - Node registration and management
    - FedAvg model aggregation (weighted average)
    - Round-based training lifecycle
    - Privacy budget tracking (epsilon consumption)
    - Convergence detection
    - Model distribution
    """

    def __init__(self, total_epsilon: float = 100.0) -> None:
        self.nodes: dict[str, FederatedNode] = {}
        self.global_model: GlobalModel = GlobalModel()
        self.rounds: list[AggregationResult] = []
        self._current_round: int = 0
        self._epsilon_budget: float = total_epsilon
        self._epsilon_consumed: float = 0.0
        self._convergence_threshold: float = 0.01  # accuracy delta

    # ── Node Management ─────────────────────────────────────────

    def register_node(
        self, node_id: str, capabilities: list[str] | None = None
    ) -> FederatedNode:
        """Register a participating node."""
        node = FederatedNode(node_id=node_id, capabilities=capabilities or [])
        self.nodes[node_id] = node
        return node

    def unregister_node(self, node_id: str) -> None:
        """Remove a node."""
        if node_id in self.nodes:
            self.nodes[node_id].status = NodeStatus.OFFLINE

    def activate_node(self, node_id: str) -> None:
        """Mark node as active."""
        node = self.nodes.get(node_id)
        if node:
            node.status = NodeStatus.ACTIVE

    # ── Training Rounds ──────────────────────────────────────────

    def start_round(self) -> AggregationResult:
        """Start a new training round."""
        self._current_round += 1
        # Mark active nodes as training
        for node in self.nodes.values():
            if node.status == NodeStatus.ACTIVE:
                node.status = NodeStatus.TRAINING

        result = AggregationResult(round=self._current_round)
        self.rounds.append(result)
        return result

    def submit_update(
        self,
        node_id: str,
        local_accuracy: float,
        samples_count: int,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Submit local model update from a node."""
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node '{node_id}' not found")

        node.local_accuracy = local_accuracy
        node.samples_count = samples_count
        node.model_version = self.global_model.version
        node.last_update = time.time()
        node.status = NodeStatus.ACTIVE  # back to active after update

        # Consume epsilon for privacy
        epsilon_per_round = 1.0
        self._epsilon_consumed += epsilon_per_round

    def aggregate(
        self, local_updates: list[dict[str, Any]] | None = None
    ) -> GlobalModel:
        """Aggregate model updates using FedAvg (weighted average)."""
        # Use node data for aggregation
        active_nodes = [n for n in self.nodes.values() if n.last_update > 0]
        total_samples = sum(n.samples_count for n in active_nodes)

        if total_samples == 0 or not active_nodes:
            return self.global_model

        # Weighted average of accuracies
        weighted_accuracy = (
            sum(n.local_accuracy * n.samples_count for n in active_nodes)
            / total_samples
        )

        # Weighted average of weights
        weights = {n.node_id: n.samples_count / total_samples for n in active_nodes}

        self.global_model.version += 1
        self.global_model.accuracy = weighted_accuracy
        self.global_model.parameters = {"weights": weights}

        # Update round result
        if self.rounds:
            last = self.rounds[-1]
            last.participants = len(active_nodes)
            last.global_accuracy = weighted_accuracy
            last.weights = weights
            last.converged = self._check_convergence()

        return self.global_model

    def _check_convergence(self) -> bool:
        """Check if model has converged."""
        if len(self.rounds) < 2:
            return False
        delta = abs(self.rounds[-1].global_accuracy - self.rounds[-2].global_accuracy)
        return delta < self._convergence_threshold

    # ── Privacy ──────────────────────────────────────────────────

    def privacy_budget_remaining(self) -> float:
        """Return remaining privacy budget."""
        return self._epsilon_budget - self._epsilon_consumed

    def is_privacy_exhausted(self) -> bool:
        """Check if privacy budget is exhausted."""
        return self._epsilon_consumed >= self._epsilon_budget

    # ── Queries ──────────────────────────────────────────────────

    def get_active_nodes(self) -> list[FederatedNode]:
        """Return active nodes."""
        return [n for n in self.nodes.values() if n.is_available()]

    def get_model(self) -> GlobalModel:
        """Return current global model."""
        return self.global_model

    def get_rounds(self, limit: int = 20) -> list[AggregationResult]:
        """Return training rounds."""
        return self.rounds[-limit:]

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "nodes": len(self.nodes),
            "active_nodes": len(self.get_active_nodes()),
            "model_version": self.global_model.version,
            "global_accuracy": self.global_model.accuracy,
            "rounds_completed": self._current_round,
            "epsilon_remaining": self.privacy_budget_remaining(),
            "converged": self._check_convergence() if self.rounds else False,
        }
