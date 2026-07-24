"""Health Checks for AIOS v10.5.0.

Enhanced health check registry with liveness/readiness/startup distinction,
dependency checks, aggregate health status, TTL caching, and periodic checks.

Classes:
    CheckKind      — LIVENESS / READINESS / STARTUP
    HealthResult   — single check result with status and details
    HealthCheckRegistry — enhanced registry with kinds, TTL, aggregate status
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class CheckKind(str, Enum):
    """Health check types (Kubernetes-inspired)."""
    LIVENESS = "liveness"    # is the process alive?
    READINESS = "readiness"  # is it ready to serve traffic?
    STARTUP = "startup"      # has it finished initializing?


# ── Health Result ────────────────────────────────────────────────────────────

@dataclass
class HealthResult:
    """Single health check result."""
    name: str
    kind: CheckKind
    status: str = "healthy"  # healthy, unhealthy, degraded, error
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None


# ── Health Check Entry ──────────────────────────────────────────────────────

@dataclass
class _HealthCheckEntry:
    """Internal: registered check with metadata."""
    name: str
    check_fn: Callable
    kind: CheckKind
    interval: float = 30.0
    ttl: float = 30.0
    last_run: float = 0.0
    cached_result: Optional[HealthResult] = None
    dependencies: list[str] = field(default_factory=list)

    def is_stale(self) -> bool:
        """Check if cached result is past TTL."""
        return time.time() - self.last_run > self.ttl


# ── Health Check Registry ───────────────────────────────────────────────────

class HealthCheckRegistry:
    """Enhanced health check registry with kinds, TTL, aggregate status.

    Features:
    - Liveness/Readiness/Startup distinction (Kubernetes model)
    - TTL caching (don't re-run checks within TTL window)
    - Dependency checks (service A depends on service B)
    - Aggregate health status computation
    - Periodic check execution
    """

    def __init__(self) -> None:
        self.checks: dict[str, _HealthCheckEntry] = {}

    # ── Registration ─────────────────────────────────────────────

    def register(self, name: str, check_fn: Callable, kind: CheckKind = CheckKind.READINESS,
                 interval: float = 30.0, ttl: float = 30.0, dependencies: list[str] | None = None) -> None:
        """Register a health check with kind and dependencies."""
        self.checks[name] = _HealthCheckEntry(
            name=name, check_fn=check_fn, kind=kind,
            interval=interval, ttl=ttl,
            dependencies=dependencies or [],
        )

    def unregister(self, name: str) -> None:
        """Remove a health check."""
        del self.checks[name]

    # ── Execution ────────────────────────────────────────────────

    def run_check(self, name: str) -> HealthResult:
        """Run a single health check."""
        entry = self.checks.get(name)
        if entry is None:
            raise KeyError(f"Health check '{name}' not found")

        # Use cached result if fresh
        if entry.cached_result and not entry.is_stale():
            return entry.cached_result

        # Check dependencies first
        for dep_name in entry.dependencies:
            dep_entry = self.checks.get(dep_name)
            if dep_entry and not self._is_healthy(dep_name):
                result = HealthResult(
                    name=name, kind=entry.kind,
                    status="degraded",
                    details={"dependency": dep_name, "dependency_status": "unhealthy"},
                )
                entry.last_run = time.time()
                entry.cached_result = result
                return result

        # Execute check
        start = time.time()
        try:
            check_result = entry.check_fn()
            duration = (time.time() - start) * 1000

            if isinstance(check_result, bool):
                status = "healthy" if check_result else "unhealthy"
                details = {}
            elif isinstance(check_result, dict):
                status = check_result.get("status", "healthy")
                details = check_result
            else:
                status = "healthy"
                details = {"value": check_result}

            result = HealthResult(
                name=name, kind=entry.kind, status=status,
                duration_ms=round(duration, 2), details=details,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = HealthResult(
                name=name, kind=entry.kind, status="error",
                duration_ms=round(duration, 2), error=str(e),
            )

        entry.last_run = time.time()
        entry.cached_result = result
        return result

    def run_all(self, kind: CheckKind | None = None) -> dict[str, HealthResult]:
        """Run all health checks, optionally filtered by kind."""
        results = {}
        for name, entry in self.checks.items():
            if kind and entry.kind != kind:
                continue
            results[name] = self.run_check(name)
        return results

    def _is_healthy(self, name: str) -> bool:
        """Quick health check using cached result."""
        entry = self.checks.get(name)
        if entry is None:
            return False
        if entry.cached_result and not entry.is_stale():
            return entry.cached_result.status in ("healthy", "degraded")
        # Need to actually run the check
        result = self.run_check(name)
        return result.status in ("healthy", "degraded")

    # ── Aggregate Status ─────────────────────────────────────────

    def overall_status(self) -> str:
        """Compute aggregate health: healthy, degraded, unhealthy."""
        results = self.run_all()
        statuses = [r.status for r in results.values()]

        if not statuses:
            return "healthy"

        if all(s == "healthy" for s in statuses):
            return "healthy"
        if any(s == "unhealthy" or s == "error" for s in statuses):
            return "unhealthy"
        return "degraded"

    def liveness_status(self) -> str:
        """Return liveness aggregate status."""
        results = self.run_all(kind=CheckKind.LIVENESS)
        if not results:
            return "healthy"
        statuses = [r.status for r in results.values()]
        return "healthy" if all(s == "healthy" for s in statuses) else "unhealthy"

    def readiness_status(self) -> str:
        """Return readiness aggregate status."""
        results = self.run_all(kind=CheckKind.READINESS)
        if not results:
            return "ready"
        statuses = [r.status for r in results.values()]
        if all(s == "healthy" for s in statuses):
            return "ready"
        if any(s == "unhealthy" or s == "error" for s in statuses):
            return "not_ready"
        return "partially_ready"

    def startup_status(self) -> str:
        """Return startup aggregate status."""
        results = self.run_all(kind=CheckKind.STARTUP)
        if not results:
            return "started"
        statuses = [r.status for r in results.values()]
        return "started" if all(s == "healthy" for s in statuses) else "starting"

    # ── Summary ──────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Return full health summary."""
        results = self.run_all()
        return {
            "overall": self.overall_status(),
            "liveness": self.liveness_status(),
            "readiness": self.readiness_status(),
            "startup": self.startup_status(),
            "checks": {name: {"status": r.status, "kind": r.kind.value, "duration_ms": r.duration_ms}
                       for name, r in results.items()},
        }

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return registry statistics."""
        by_kind: dict[str, int] = {}
        for entry in self.checks.values():
            by_kind[entry.kind.value] = by_kind.get(entry.kind.value, 0) + 1
        return {
            "total_checks": len(self.checks),
            "by_kind": by_kind,
            "overall": self.overall_status(),
        }


health_registry = HealthCheckRegistry()
