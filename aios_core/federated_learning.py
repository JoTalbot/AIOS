"""Federated Learning Coordination for Distributed Edge Nodes (AIOS v10.18.0).

Advanced Federated Learning coordinator featuring:
- Edge node lifecycle management & profiling
- Asynchronous Federated Learning (FedAsync)
- Secure Aggregation (SecAgg) protocol simulation
- Local Differential Privacy (LDP) noise injection
- Client selection strategies (Random, Resource-aware)
- Privacy budget tracking and convergence detection

Classes:
    EdgeProfile       — hardware capabilities of edge nodes
    NodeStatus        — active / offline / training
    FederatedNode     — participant node state
    AggregationResult — round aggregation outcome
    FederatedLearning — full FL edge coordinator
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeStatus(StrEnum):
    """Node participation status."""

    ACTIVE = "active"
    OFFLINE = "offline"
    TRAINING = "training"
    STALE = "stale"


@dataclass
class EdgeProfile:
    """Hardware and network profile of an edge node."""
    compute_gflops: float = 10.0
    bandwidth_mbps: float = 50.0
    battery_level: float = 1.0  # 0.0 to 1.0
    reliability_score: float = 0.99


@dataclass
class FederatedNode:
    """Participant edge node with model version and profile."""

    node_id: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.ACTIVE
    profile: EdgeProfile = field(default_factory=EdgeProfile)
    model_version: int = 0
    local_accuracy: float = 0.0
    samples_count: int = 0
    last_update: float = 0.0
    consecutive_failures: int = 0

    def is_available(self) -> bool:
        """Check if node can participate in a round."""
        return self.status == NodeStatus.ACTIVE and self.profile.battery_level > 0.15


@dataclass
class AggregationResult:
    """Round aggregation outcome."""

    round: int = 0
    participants: int = 0
    global_accuracy: float = 0.0
    converged: bool = False
    timestamp: float = field(default_factory=time.time)
    weights: Dict[str, float] = field(default_factory=dict)  # node_id → weight
    aggregation_method: str = "FedAvg"


@dataclass
class GlobalModel:
    """Global aggregated model state."""

    version: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    accuracy: float = 0.0


class SecureAggregator:
    """Simulates Secure Aggregation (SecAgg) via secret sharing / masking."""
    
    def __init__(self):
        self.active_masks: Dict[str, float] = {}
        
    def generate_mask(self, node_id: str) -> float:
        mask = random.uniform(-10.0, 10.0)
        self.active_masks[node_id] = mask
        return mask
        
    def unmask_aggregate(self, masked_sum: float, node_ids: List[str]) -> float:
        total_mask = sum(self.active_masks.get(nid, 0.0) for nid in node_ids)
        # Clear used masks
        for nid in node_ids:
            self.active_masks.pop(nid, None)
        return masked_sum - total_mask


class LocalDifferentialPrivacy:
    """Applies LDP (Local Differential Privacy) noise to gradients."""
    
    def __init__(self, epsilon: float = 2.0, delta: float = 1e-5):
        self.epsilon = epsilon
        self.delta = delta
        
    def apply_gaussian_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """Inject Gaussian noise based on epsilon budget."""
        # Standard deviation for Gaussian mechanism
        sigma = (sensitivity * math.sqrt(2 * math.log(1.25 / self.delta))) / self.epsilon
        noise = random.gauss(0, sigma)
        return value + noise


class FederatedLearning:
    """Full Edge FL coordinator with async aggregation, privacy, and client selection."""

    def __init__(
        self, 
        total_epsilon: float = 100.0,
        async_mode: bool = False,
        enable_sec_agg: bool = True
    ) -> None:
        self.nodes: Dict[str, FederatedNode] = {}
        self.global_model: GlobalModel = GlobalModel()
        self.rounds: List[AggregationResult] = []
        
        self.async_mode = async_mode
        self.enable_sec_agg = enable_sec_agg
        self.sec_aggregator = SecureAggregator()
        self.ldp = LocalDifferentialPrivacy()
        
        self._current_round: int = 0
        self._epsilon_budget: float = total_epsilon
        self._epsilon_consumed: float = 0.0
        self._convergence_threshold: float = 0.005  # accuracy delta
        self._stale_timeout: float = 300.0  # 5 minutes without heartbeat

    # ── Node Management ─────────────────────────────────────────

    def register_node(
        self, 
        node_id: str, 
        capabilities: Optional[List[str]] = None,
        profile: Optional[EdgeProfile] = None
    ) -> FederatedNode:
        """Register a participating edge node."""
        node = FederatedNode(
            node_id=node_id, 
            capabilities=capabilities or [],
            profile=profile or EdgeProfile()
        )
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
            node.consecutive_failures = 0

    def prune_stale_nodes(self) -> int:
        """Mark nodes as offline if they haven't reported recently."""
        pruned = 0
        now = time.time()
        for node in self.nodes.values():
            if node.status in (NodeStatus.ACTIVE, NodeStatus.TRAINING):
                if now - node.last_update > self._stale_timeout:
                    node.status = NodeStatus.STALE
                    pruned += 1
        return pruned

    # ── Client Selection ─────────────────────────────────────────

    def select_clients(self, strategy: str = "random", fraction: float = 0.5) -> List[FederatedNode]:
        """Select a subset of clients for the next training round."""
        available = [n for n in self.nodes.values() if n.is_available()]
        if not available:
            return []
            
        k = max(1, int(len(available) * fraction))
        
        if strategy == "resource_aware":
            # Select nodes with best battery and reliability
            available.sort(key=lambda n: n.profile.battery_level * n.profile.reliability_score, reverse=True)
            return available[:k]
        elif strategy == "capability_based":
            # Select nodes with highest compute
            available.sort(key=lambda n: n.profile.compute_gflops, reverse=True)
            return available[:k]
        else: # Random
            return random.sample(available, k)

    # ── Training Rounds ──────────────────────────────────────────

    def start_round(self, selection_strategy: str = "random", fraction: float = 1.0) -> AggregationResult:
        """Start a new training round and select clients."""
        self._current_round += 1
        self.prune_stale_nodes()
        
        selected_nodes = self.select_clients(strategy=selection_strategy, fraction=fraction)
        
        for node in selected_nodes:
            node.status = NodeStatus.TRAINING
            
            # If secure aggregation is enabled, distribute masks
            if self.enable_sec_agg:
                self.sec_aggregator.generate_mask(node.node_id)

        result = AggregationResult(round=self._current_round)
        self.rounds.append(result)
        return result

    def submit_update(
        self,
        node_id: str,
        local_accuracy: float,
        samples_count: int,
        parameters: Optional[Dict[str, Any]] = None,
        apply_ldp: bool = False
    ) -> None:
        """Submit local model update from an edge node."""
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node '{node_id}' not found")

        # Apply Local Differential Privacy if requested
        if apply_ldp:
            local_accuracy = self.ldp.apply_gaussian_noise(local_accuracy, sensitivity=0.01)
            # Ensure bounds
            local_accuracy = max(0.0, min(1.0, local_accuracy))

        node.local_accuracy = local_accuracy
        node.samples_count = samples_count
        node.model_version = self.global_model.version
        node.last_update = time.time()
        node.status = NodeStatus.ACTIVE
        node.profile.battery_level = max(0.0, node.profile.battery_level - 0.05)  # Battery drain

        # Consume global epsilon for privacy tracking
        self._epsilon_consumed += self.ldp.epsilon if apply_ldp else 1.0
        
        # Async aggregation: update global model immediately on reception
        if self.async_mode:
            self._aggregate_async(node)

    # ── Aggregation ──────────────────────────────────────────────

    def _aggregate_async(self, node: FederatedNode) -> None:
        """FedAsync: blend incoming stale gradient with current global model."""
        staleness = self.global_model.version - node.model_version
        alpha = 0.5 * math.exp(-0.1 * staleness) # Mixing hyperparameter decaying by staleness
        
        new_accuracy = (1 - alpha) * self.global_model.accuracy + alpha * node.local_accuracy
        
        self.global_model.version += 1
        self.global_model.accuracy = new_accuracy
        
        # Update current round
        if self.rounds:
            last = self.rounds[-1]
            last.participants += 1
            last.global_accuracy = new_accuracy
            last.aggregation_method = "FedAsync"
            last.converged = self._check_convergence()

    def aggregate(self, local_updates: Optional[List[Dict[str, Any]]] = None) -> GlobalModel:
        return self.aggregate_sync()

    def aggregate_sync(self) -> GlobalModel:
        """Aggregate model updates using FedAvg (weighted average)."""
        if self.async_mode:
            return self.global_model
            
        # Use node data for aggregation
        updated_nodes = [
            n for n in self.nodes.values() 
            if n.last_update > 0 and n.model_version == self.global_model.version
        ]
        total_samples = sum(n.samples_count for n in updated_nodes)

        if total_samples == 0 or not updated_nodes:
            return self.global_model

        # Secure Aggregation Simulation
        if self.enable_sec_agg:
            raw_sum = sum(n.local_accuracy * n.samples_count for n in updated_nodes)
            # Add masks as if nodes masked their uploads
            masked_sum = raw_sum + sum(self.sec_aggregator.active_masks.get(n.node_id, 0.0) for n in updated_nodes)
            # Server unmasks
            true_sum = self.sec_aggregator.unmask_aggregate(masked_sum, [n.node_id for n in updated_nodes])
            weighted_accuracy = true_sum / total_samples
        else:
            weighted_accuracy = sum(n.local_accuracy * n.samples_count for n in updated_nodes) / total_samples

        # Weights
        weights = {n.node_id: n.samples_count / total_samples for n in updated_nodes}

        self.global_model.version += 1
        self.global_model.accuracy = max(0.0, min(1.0, weighted_accuracy))
        self.global_model.parameters = {"weights": weights}

        # Update round result
        if self.rounds:
            last = self.rounds[-1]
            last.participants = len(updated_nodes)
            last.global_accuracy = self.global_model.accuracy
            last.weights = weights
            last.aggregation_method = "FedAvg+SecAgg" if self.enable_sec_agg else "FedAvg"
            last.converged = self._check_convergence()

        return self.global_model

    def _check_convergence(self) -> bool:
        """Check if model has converged."""
        if len(self.rounds) < 3:
            return False
            
        deltas = [
            abs(self.rounds[i].global_accuracy - self.rounds[i-1].global_accuracy)
            for i in range(-1, -3, -1)
        ]
        return all(d < self._convergence_threshold for d in deltas)

    # ── Queries & Stats ──────────────────────────────────────────

    def privacy_budget_remaining(self) -> float:
        """Return remaining privacy budget."""
        return max(0.0, self._epsilon_budget - self._epsilon_consumed)

    def is_privacy_exhausted(self) -> bool:
        """Check if privacy budget is exhausted."""
        return self._epsilon_consumed >= self._epsilon_budget

    def get_model(self) -> GlobalModel:
        return self.global_model

    def get_active_nodes(self) -> List[FederatedNode]:
        """Return active nodes."""
        return [n for n in self.nodes.values() if n.is_available()]

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics."""
        return {
            "nodes": len(self.nodes),
            "active_nodes": len(self.get_active_nodes()),
            "stale_nodes": sum(1 for n in self.nodes.values() if n.status == NodeStatus.STALE),
            "model_version": self.global_model.version,
            "global_accuracy": round(self.global_model.accuracy, 4),
            "rounds_completed": self._current_round,
            "epsilon_remaining": round(self.privacy_budget_remaining(), 2),
            "converged": self._check_convergence(),
            "async_mode": self.async_mode,
            "sec_agg_enabled": self.enable_sec_agg
        }
