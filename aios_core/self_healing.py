"""Self-Healing System for AIOS v10.5.0.

Automatic recovery from failures with strategy registry, health monitoring,
escalation levels, circuit breaker integration, diagnostic analysis,
recovery history, and configurable thresholds.

Classes:
    RecoveryLevel   — escalation severity (LIGHT → CRITICAL)
    RecoveryRecord  — audit entry for each healing attempt
    HealthMonitor   — periodic check registry with TTL caching
    SelfHealing     — enhanced recovery engine with escalation, diagnostics, history
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class RecoveryLevel(str, Enum):
    """Recovery escalation severity."""
    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


# ── Recovery Record ──────────────────────────────────────────────────────────

@dataclass
class RecoveryRecord:
    """Audit entry for a recovery attempt."""
    error_type: str
    strategy_name: str
    level: RecoveryLevel
    success: bool
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)


# ── Health Monitor ───────────────────────────────────────────────────────────

@dataclass
class HealthCheck:
    """Named health check function with TTL cache."""
    name: str
    check_fn: Callable[[], bool]
    interval: float = 30.0  # seconds between checks
    last_run: float = 0.0
    last_result: bool = True
    ttl: float = 30.0  # cache validity

    def is_stale(self) -> bool:
        """Return True if the cached result is past its TTL."""
        return time.time() - self.last_run > self.ttl

    def run(self) -> bool:
        """Execute the check and cache the result."""
        self.last_run = time.time()
        try:
            self.last_result = self.check_fn()
        except Exception:
            self.last_result = False
        return self.last_result

    def cached_result(self) -> bool:
        """Return cached result if fresh, otherwise re-run."""
        if self.is_stale():
            return self.run()
        return self.last_result


class HealthMonitor:
    """Periodic health check registry with TTL caching."""

    def __init__(self) -> None:
        self.checks: dict[str, HealthCheck] = {}

    def register(self, name: str, check_fn: Callable[[], bool], interval: float = 30.0) -> None:
        """Register a health check."""
        self.checks[name] = HealthCheck(name=name, check_fn=check_fn, interval=interval)

    def run_all(self) -> dict[str, bool]:
        """Run all stale checks and return results."""
        results = {}
        for name, check in self.checks.items():
            results[name] = check.cached_result()
        return results

    def overall_healthy(self) -> bool:
        """Return True if all checks pass."""
        return all(check.cached_result() for check in self.checks.values())

    def unhealthy_services(self) -> list[str]:
        """Return names of services currently unhealthy."""
        return [name for name, check in self.checks.items() if not check.cached_result()]


# ── Self-Healing ─────────────────────────────────────────────────────────────

class SelfHealing:
    """Enhanced recovery engine with escalation, diagnostics, and history.

    Maintains a registry of error-type → recovery strategy mappings
    with configurable escalation levels, health monitoring integration,
    diagnostic analysis, and recovery history tracking.
    """

    def __init__(self, max_recovery_attempts: int = 3, escalation_threshold: int = 2) -> None:
        """Initialize SelfHealing.

        Args:
            max_recovery_attempts: Maximum retries for a single error type.
            escalation_threshold: Failures before escalating recovery level.
        """
        self.recovery_strategies: dict[str, Callable] = {}
        self.strategy_levels: dict[str, RecoveryLevel] = {}
        self.recovery_history: list[RecoveryRecord] = []
        self.health_monitor: HealthMonitor = HealthMonitor()
        self._attempt_counts: dict[str, int] = {}
        self.max_recovery_attempts = max_recovery_attempts
        self.escalation_threshold = escalation_threshold

    def register_strategy(self, error_type: str, strategy: Callable, level: RecoveryLevel = RecoveryLevel.LIGHT) -> None:
        """Register a recovery strategy for a given error type name."""
        self.recovery_strategies[error_type] = strategy
        self.strategy_levels[error_type] = level

    def register_health_check(self, name: str, check_fn: Callable[[], bool], interval: float = 30.0) -> None:
        """Register a health check for monitoring."""
        self.health_monitor.register(name, check_fn, interval)

    def heal(self, error: Exception, context: dict[str, Any] | None = None) -> bool:
        """Attempt to heal from a failure by invoking the registered strategy.

        Includes escalation: if same error type fails repeatedly, recovery
        level increases from LIGHT → MODERATE → SEVERE → CRITICAL.
        """
        context = context or {}
        error_type = type(error).__name__

        if error_type not in self.recovery_strategies:
            logger.warning("No recovery strategy for '%s'", error_type)
            return False

        # Track attempts for escalation
        self._attempt_counts[error_type] = self._attempt_counts.get(error_type, 0) + 1
        attempts = self._attempt_counts[error_type]

        # Escalate level based on attempt count
        base_level = self.strategy_levels.get(error_type, RecoveryLevel.LIGHT)
        level = self._escalate(base_level, attempts)

        # Check max attempts
        if attempts > self.max_recovery_attempts:
            logger.error("Max recovery attempts (%d) exceeded for '%s'", self.max_recovery_attempts, error_type)
            return False

        # Execute strategy
        start = time.time()
        try:
            self.recovery_strategies[error_type](context)
            duration = time.time() - start
            self.recovery_history.append(RecoveryRecord(
                error_type=error_type,
                strategy_name=error_type,
                level=level,
                success=True,
                duration=duration,
                context=context,
            ))
            # Reset attempt count on success
            self._attempt_counts[error_type] = 0
            logger.info("Successfully recovered from '%s' (level=%s, attempt=%d)", error_type, level.value, attempts)
            return True
        except Exception as exc:
            duration = time.time() - start
            self.recovery_history.append(RecoveryRecord(
                error_type=error_type,
                strategy_name=error_type,
                level=level,
                success=False,
                duration=duration,
                context=context,
            ))
            logger.error("Recovery strategy for '%s' failed: %s (level=%s)", error_type, exc, level.value)
            return False

    def diagnose(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run diagnostic analysis — health checks + recovery history."""
        context = context or {}
        health = self.health_monitor.run_all()
        recent = self.recovery_history[-10:]
        failed_types = [r.error_type for r in self.recovery_history if not r.success]
        return {
            "healthy": health,
            "overall_healthy": self.health_monitor.overall_healthy(),
            "unhealthy_services": self.health_monitor.unhealthy_services(),
            "recent_recoveries": [{"error": r.error_type, "success": r.success, "level": r.level.value} for r in recent],
            "recurring_errors": list(set(failed_types)),
            "strategies_registered": len(self.recovery_strategies),
        }

    def _escalate(self, base_level: RecoveryLevel, attempts: int) -> RecoveryLevel:
        """Escalate recovery level based on attempt count."""
        levels = [RecoveryLevel.LIGHT, RecoveryLevel.MODERATE, RecoveryLevel.SEVERE, RecoveryLevel.CRITICAL]
        base_idx = levels.index(base_level)
        extra = (attempts - 1) // self.escalation_threshold
        new_idx = min(base_idx + extra, len(levels) - 1)
        return levels[new_idx]

    def reset_attempts(self, error_type: str | None = None) -> None:
        """Reset attempt counters."""
        if error_type:
            self._attempt_counts.pop(error_type, None)
        else:
            self._attempt_counts.clear()

    def stats(self) -> dict[str, Any]:
        """Return statistics about recovery system."""
        success_count = sum(1 for r in self.recovery_history if r.success)
        return {
            "strategies": len(self.recovery_strategies),
            "recovery_attempts": len(self.recovery_history),
            "successful_recoveries": success_count,
            "success_rate": success_count / len(self.recovery_history) if self.recovery_history else 0.0,
            "health_checks": len(self.health_monitor.checks),
        }
