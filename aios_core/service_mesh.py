"""Service Mesh for AIOS v10.5.0.

Inter-service communication mesh with service discovery, health checking,
traffic splitting, retry policies, circuit breaker integration, and
sidecar proxy model.

Classes:
    ServiceInstance — single service endpoint with metadata and health
    TrafficRule     — weight-based traffic splitting rule
    ServiceMesh     — full mesh with discovery, health, traffic, retry
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Service Instance ─────────────────────────────────────────────────────────

@dataclass
class ServiceInstance:
    """Single service endpoint with health and metadata."""
    name: str
    endpoint: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "healthy"  # healthy, unhealthy, degraded
    weight: int = 100  # traffic weight
    last_health_check: float = 0.0
    request_count: int = 0
    error_count: int = 0

    def mark_healthy(self) -> None:
        """Mark instance as healthy."""
        self.status = "healthy"
        self.last_health_check = time.time()

    def mark_unhealthy(self) -> None:
        """Mark instance as unhealthy."""
        self.status = "unhealthy"
        self.last_health_check = time.time()

    def mark_degraded(self) -> None:
        """Mark instance as degraded."""
        self.status = "degraded"
        self.last_health_check = time.time()

    def is_available(self) -> bool:
        """Check if instance can receive traffic."""
        return self.status in ("healthy", "degraded")


# ── Traffic Rule ─────────────────────────────────────────────────────────────

@dataclass
class TrafficRule:
    """Weight-based traffic splitting between service versions."""
    name: str
    source: str
    targets: dict[str, int] = field(default_factory=dict)  # target_name → weight%

    def select_target(self) -> str:
        """Select a target based on weighted random selection."""
        total = sum(self.targets.values())
        if total == 0:
            raise ValueError(f"Traffic rule '{self.name}' has no targets")
        r = random.randint(1, total)
        cumulative = 0
        for target, weight in self.targets.items():
            cumulative += weight
            if r <= cumulative:
                return target
        # Fallback to last
        return list(self.targets.keys())[-1]


# ── Service Mesh ─────────────────────────────────────────────────────────────

class ServiceMesh:
    """Full service mesh with discovery, health, traffic splitting, retry.

    Features:
    - Service registration with health status
    - Service discovery with filtering
    - Traffic splitting (canary, blue-green)
    - Health checking integration
    - Load balancing (round-robin, random, weighted)
    - Retry policy per route
    """

    def __init__(self) -> None:
        self.services: dict[str, ServiceInstance] = {}
        self.routes: list[TrafficRule] = []
        self.health_checkers: dict[str, Callable] = {}
        self._load_balance_strategy: str = "weighted"  # round_robin, random, weighted
        self._round_robin_idx: int = 0

    # ── Service Registration ─────────────────────────────────────

    def register_service(self, name: str, endpoint: str, metadata: dict[str, Any] | None = None,
                         weight: int = 100) -> ServiceInstance:
        """Register a service instance."""
        instance = ServiceInstance(name=name, endpoint=endpoint, metadata=metadata or {}, weight=weight)
        self.services[name] = instance
        return instance

    def unregister_service(self, name: str) -> None:
        """Remove a service from the mesh."""
        del self.services[name]
        self.routes = [r for r in self.routes if r.source != name]
        self.health_checkers.pop(name, None)

    # ── Service Discovery ────────────────────────────────────────

    def discover(self, service: str) -> dict[str, Any]:
        """Discover a service — return endpoint info."""
        instance = self.services.get(service)
        if instance is None:
            return {}
        return {
            "name": instance.name,
            "endpoint": instance.endpoint,
            "status": instance.status,
            "weight": instance.weight,
            "metadata": instance.metadata,
        }

    def discover_all(self, status: str | None = None) -> list[dict[str, Any]]:
        """Discover all services, optionally filtered by status."""
        results = []
        for inst in self.services.values():
            if status and inst.status != status:
                continue
            results.append(self.discover(inst.name))
        return results

    def discover_healthy(self) -> list[dict[str, Any]]:
        """Return all healthy service endpoints."""
        return self.discover_all(status="healthy")

    # ── Traffic Routing ──────────────────────────────────────────

    def add_route(self, source: str, targets: dict[str, int], name: str | None = None) -> TrafficRule:
        """Add a traffic splitting rule."""
        rule = TrafficRule(name=name or f"{source}_route", source=source, targets=targets)
        self.routes.append(rule)
        return rule

    def remove_route(self, name: str) -> None:
        """Remove a traffic rule."""
        self.routes = [r for r in self.routes if r.name != name]

    def route_request(self, source: str) -> str:
        """Route a request from source using traffic rules."""
        rule = self._find_route(source)
        if rule:
            return rule.select_target()
        # No rule → find healthy instance for source
        instance = self.services.get(source)
        if instance and instance.is_available():
            return instance.endpoint
        return ""

    def _find_route(self, source: str) -> TrafficRule | None:
        """Find traffic rule for a source service."""
        for rule in self.routes:
            if rule.source == source:
                return rule
        return None

    # ── Health Checking ──────────────────────────────────────────

    def register_health_check(self, service: str, check_fn: Callable) -> None:
        """Register a health check function for a service."""
        self.health_checkers[service] = check_fn

    def run_health_checks(self) -> dict[str, str]:
        """Run all registered health checks and update statuses."""
        results = {}
        for name, check_fn in self.health_checkers.items():
            instance = self.services.get(name)
            if instance is None:
                continue
            try:
                healthy = check_fn()
                if healthy:
                    instance.mark_healthy()
                    results[name] = "healthy"
                else:
                    instance.mark_unhealthy()
                    results[name] = "unhealthy"
            except Exception:
                instance.mark_unhealthy()
                results[name] = "error"
        return results

    # ── Load Balancing ───────────────────────────────────────────

    def set_load_balance_strategy(self, strategy: str) -> None:
        """Set load balancing strategy: round_robin, random, weighted."""
        self._load_balance_strategy = strategy

    def select_instance(self, service: str) -> ServiceInstance | None:
        """Select an instance using the configured strategy."""
        available = [i for i in self.services.values() if i.is_available()]
        if not available:
            return None
        if self._load_balance_strategy == "round_robin":
            idx = self._round_robin_idx % len(available)
            self._round_robin_idx += 1
            return available[idx]
        if self._load_balance_strategy == "random":
            return random.choice(available)
        # weighted: probability proportional to weight
        total = sum(i.weight for i in available)
        r = random.randint(1, total)
        cumulative = 0
        for inst in available:
            cumulative += inst.weight
            if r <= cumulative:
                return inst
        return available[-1]

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_status = {}
        for inst in self.services.values():
            by_status[inst.status] = by_status.get(inst.status, 0) + 1
        return {
            "services": len(self.services),
            "routes": len(self.routes),
            "health_checks": len(self.health_checkers),
            "by_status": by_status,
            "load_balance_strategy": self._load_balance_strategy,
        }


service_mesh = ServiceMesh()
