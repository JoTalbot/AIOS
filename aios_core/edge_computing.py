"""Edge Computing Support for AIOS v10.7.0.

Edge node orchestration with location-based scheduling, latency
estimation, node health, task offloading, and capacity management.

Classes:
    EdgeNode       — edge computing node with location and capacity
    EdgeOrchestrator — full orchestrator with scheduling, health, offloading
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EdgeNode:
    """Edge computing node with location and capacity."""
    node_id: str = ""
    location: str = ""
    capacity: int = 100
    load: int = 0
    latency_ms: float = 50.0  # estimated latency
    health: str = "healthy"  # healthy, degraded, offline
    capabilities: list[str] = field(default_factory=list)
    task_count: int = 0
    failed_count: int = 0
    last_heartbeat: float = field(default_factory=time.time)

    def can_handle(self, task_size: int) -> bool:
        """Check if node can accept a task."""
        return self.health != "offline" and self.load + task_size <= self.capacity

    def assign(self, task_size: int) -> None:
        """Assign task to node."""
        self.load += task_size
        self.task_count += 1
        self.last_heartbeat = time.time()

    def release(self, task_size: int, success: bool = True) -> None:
        """Release task from node."""
        self.load -= task_size
        if not success:
            self.failed_count += 1

    def utilization(self) -> float:
        """Return utilization percentage (0..100)."""
        if self.capacity == 0:
            return 0.0
        return self.load / self.capacity * 100.0

    def mark_offline(self) -> None:
        """Mark node as offline."""
        self.health = "offline"

    def mark_degraded(self) -> None:
        """Mark node as degraded."""
        self.health = "degraded"

    def mark_healthy(self) -> None:
        """Mark node as healthy."""
        self.health = "healthy"


class EdgeOrchestrator:
    """Full edge orchestrator with scheduling, health, and offloading.

    Features:
    - Location-aware scheduling (prefer nearby nodes)
    - Latency estimation per node
    - Node health monitoring
    - Task offloading from overloaded nodes
    - Capacity-based load balancing
    """

    def __init__(self) -> None:
        self.nodes: dict[str, EdgeNode] = {}
        self._task_assignments: dict[str, str] = {}  # task_id → node_id

    # ── Node Management ─────────────────────────────────────────

    def register_node(self, node: EdgeNode) -> None:
        """Register an edge node."""
        self.nodes[node.node_id] = node

    def unregister_node(self, node_id: str) -> None:
        """Remove a node."""
        node = self.nodes.get(node_id)
        if node:
            node.mark_offline()

    # ── Scheduling ──────────────────────────────────────────────

    def schedule(self, task_size: int, preferred_location: str | None = None) -> str | None:
        """Schedule task to best node (least-loaded, preferably nearby)."""
        candidates = [n for n in self.nodes.values() if n.can_handle(task_size)]
        if not candidates:
            return None

        if preferred_location:
            # Prefer nodes in same location
            local = [n for n in candidates if n.location == preferred_location]
            if local:
                candidates = local

        # Least-loaded first
        best = min(candidates, key=lambda n: n.utilization())
        best.assign(task_size)
        return best.node_id

    def schedule_low_latency(self, task_size: int) -> str | None:
        """Schedule task to node with lowest latency."""
        candidates = [n for n in self.nodes.values() if n.can_handle(task_size)]
        if not candidates:
            return None
        best = min(candidates, key=lambda n: n.latency_ms)
        best.assign(task_size)
        return best.node_id

    def schedule_balanced(self, task_size: int) -> str | None:
        """Balance: consider both load and latency."""
        candidates = [n for n in self.nodes.values() if n.can_handle(task_size)]
        if not candidates:
            return None
        # Score = utilization + latency_weight
        best = min(candidates, key=lambda n: n.utilization() + n.latency_ms / 10)
        best.assign(task_size)
        return best.node_id

    # ── Offloading ──────────────────────────────────────────────

    def offload_overloaded(self, threshold: float = 90.0) -> list[str]:
        """Offload tasks from nodes above utilization threshold."""
        overloaded = [n for n in self.nodes.values() if n.utilization() > threshold and n.health != "offline"]
        offloaded: list[str] = []
        for node in overloaded:
            # Find underloaded node to receive tasks
            receivers = [n for n in self.nodes.values()
                         if n.utilization() < 50 and n.can_handle(10) and n.node_id != node.node_id]
            if receivers:
                receiver = min(receivers, key=lambda n: n.utilization())
                node.load -= 10
                receiver.assign(10)
                offloaded.append(f"{node.node_id} → {receiver.node_id}")
        return offloaded

    # ── Health Monitoring ────────────────────────────────────────

    def check_health(self) -> dict[str, str]:
        """Check node health based on heartbeat freshness."""
        now = time.time()
        results = {}
        for node in self.nodes.values():
            if node.health == "offline":
                results[node.node_id] = "offline"
                continue
            # If heartbeat is stale (> 60s), mark degraded
            if now - node.last_heartbeat > 60:
                node.mark_degraded()
                results[node.node_id] = "degraded"
            else:
                results[node.node_id] = node.health
        return results

    def get_healthy_nodes(self) -> list[EdgeNode]:
        """Return all healthy nodes."""
        self.check_health()
        return [n for n in self.nodes.values() if n.health == "healthy"]

    def get_degraded_nodes(self) -> list[EdgeNode]:
        """Return degraded nodes."""
        return [n for n in self.nodes.values() if n.health == "degraded"]

    def get_offline_nodes(self) -> list[EdgeNode]:
        """Return offline nodes."""
        return [n for n in self.nodes.values() if n.health == "offline"]

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        total_load = sum(n.load for n in self.nodes.values())
        total_capacity = sum(n.capacity for n in self.nodes.values())
        by_health: dict[str, int] = {}
        for n in self.nodes.values():
            by_health[n.health] = by_health.get(n.health, 0) + 1
        return {
            "nodes": len(self.nodes),
            "by_health": by_health,
            "total_load": total_load,
            "total_capacity": total_capacity,
            "overall_utilization": total_load / total_capacity * 100 if total_capacity else 0.0,
        }
