"""Platform health monitor — real-time monitoring of platform availability.

Provides:
- Health checks: ping platforms for availability, latency, error rates
- Health scores: composite 0-100 score per platform
- Block detection: detect when platform blocks scraping agents
- Rate limit monitoring: track current rate limit status
- Health history: track health over time for trend analysis
- Alert integration: trigger alerts when health drops below threshold
- Platform comparison: compare health across multiple platforms

No external monitoring services — uses internal metrics and observations.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    """Platform health status."""

    HEALTHY = "healthy"        # Fully operational
    DEGRADED = "degraded"      # Partially operational
    UNSTABLE = "unstable"      # Frequent failures
    BLOCKED = "blocked"        # Platform blocking agent
    DOWN = "down"              # Platform unreachable
    UNKNOWN = "unknown"        # No recent data


class CheckType(Enum):
    """Types of health checks."""

    PING = "ping"              # Basic connectivity
    SCRAPE = "scrape"          # Actual scraping test
    LOGIN = "login"            # Login attempt
    RATE_LIMIT = "rate_limit"  # Rate limit check
    BLOCK = "block"            # Block detection


@dataclass
class HealthCheck:
    """A single health check result."""

    check_id: str
    platform: str
    check_type: CheckType
    status: HealthStatus
    latency_ms: float
    success: bool
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize check to dict."""
        return {
            "check_id": self.check_id,
            "platform": self.platform,
            "type": self.check_type.value,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 1),
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class PlatformHealth:
    """Current health state of a platform."""

    platform: str
    status: HealthStatus = HealthStatus.UNKNOWN
    health_score: float = 100.0     # 0-100 composite score
    latency_ms: float = 0.0         # Average recent latency
    success_rate: float = 1.0       # Recent success rate
    error_rate: float = 0.0         # Recent error rate
    block_risk: float = 0.0         # Block detection probability
    rate_limit_remaining: int = -1  # -1 = unknown
    last_check: float | None = None
    last_success: float | None = None
    last_failure: float | None = None
    last_block: float | None = None
    checks_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_minutes(self) -> float | None:
        """Minutes since last health check."""
        if self.last_check:
            return (time.time() - self.last_check) / 60
        return None

    @property
    def is_available(self) -> bool:
        """True if platform is available for scraping."""
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    def to_dict(self) -> dict[str, Any]:
        """Serialize health to dict."""
        return {
            "platform": self.platform,
            "status": self.status.value,
            "health_score": round(self.health_score, 1),
            "latency_ms": round(self.latency_ms, 1),
            "success_rate": round(self.success_rate, 4),
            "error_rate": round(self.error_rate, 4),
            "block_risk": round(self.block_risk, 4),
            "is_available": self.is_available,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_check": self.last_check,
        }


class PlatformHealthMonitor:
    """Monitor platform health for scraping fleet optimization.

    Provides:
    - register_platform() — track a platform
    - report_check() — submit health check result
    - report_success() / report_failure() — simple reporting
    - report_block() — report detected block
    - get_health() — get current health status
    - compare_platforms() — compare health across platforms
    - detect_degradation() — find degraded platforms
    - stats() — monitoring statistics
    """

    def __init__(
        self,
        health_threshold: float = 70.0,
        block_threshold: float = 0.5,
        failure_window_minutes: float = 30.0,
        max_consecutive_failures: int = 5,
    ) -> None:
        """Initialize PlatformHealthMonitor.

        Args:
            health_threshold: Score below which platform is "degraded".
            block_threshold: Block risk above which platform is "blocked".
            failure_window_minutes: Window for computing success/error rates.
            max_consecutive_failures: Failures before marking "down".
        """
        self.health_threshold = health_threshold
        self.block_threshold = block_threshold
        self.failure_window_minutes = failure_window_minutes
        self.max_consecutive_failures = max_consecutive_failures
        self._platforms: dict[str, PlatformHealth] = {}
        self._checks: dict[str, list[HealthCheck]] = defaultdict(list)
        self._counter: int = 0

    def _next_id(self) -> str:
        """Generate unique check ID."""
        self._counter += 1
        return f"check_{self._counter}"

    def register_platform(self, platform: str) -> PlatformHealth:
        """Register a platform for monitoring.

        Args:
            platform: Platform name.

        Returns:
            PlatformHealth instance.
        """
        if platform not in self._platforms:
            self._platforms[platform] = PlatformHealth(platform=platform)
        return self._platforms[platform]

    def report_check(self, check: HealthCheck) -> PlatformHealth:
        """Submit a health check result.

        Args:
            check: HealthCheck result.

        Returns:
            Updated PlatformHealth.
        """
        # Ensure platform is registered
        if check.platform not in self._platforms:
            self.register_platform(check.platform)

        # Store check
        self._checks[check.platform].append(check)
        # Keep only recent checks (last 100)
        if len(self._checks[check.platform]) > 100:
            self._checks[check.platform] = self._checks[check.platform][-100:]

        # Update health
        return self._update_health(check.platform)

    def report_success(
        self,
        platform: str,
        latency_ms: float = 0,
        check_type: CheckType = CheckType.SCRAPE,
    ) -> PlatformHealth:
        """Report a successful operation.

        Args:
            platform: Platform name.
            latency_ms: Operation latency.
            check_type: Type of check.

        Returns:
            Updated PlatformHealth.
        """
        check = HealthCheck(
            check_id=self._next_id(),
            platform=platform,
            check_type=check_type,
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            success=True,
        )
        return self.report_check(check)

    def report_failure(
        self,
        platform: str,
        error: str = "",
        latency_ms: float = 0,
        check_type: CheckType = CheckType.SCRAPE,
    ) -> PlatformHealth:
        """Report a failed operation.

        Args:
            platform: Platform name.
            error: Error message.
            latency_ms: Operation latency.
            check_type: Type of check.

        Returns:
            Updated PlatformHealth.
        """
        health = self._platforms.get(platform)
        consecutive = health.consecutive_failures if health else 0

        status = HealthStatus.UNSTABLE if consecutive < self.max_consecutive_failures else HealthStatus.DOWN

        check = HealthCheck(
            check_id=self._next_id(),
            platform=platform,
            check_type=check_type,
            status=status,
            latency_ms=latency_ms,
            success=False,
            error=error,
        )
        return self.report_check(check)

    def report_block(
        self,
        platform: str,
        block_type: str = "rate_limit",
        details: dict[str, Any] | None = None,
    ) -> PlatformHealth:
        """Report a detected block.

        Args:
            platform: Platform name.
            block_type: Type of block (rate_limit, captcha, ip_ban, account_ban).
            details: Additional block details.

        Returns:
            Updated PlatformHealth.
        """
        check = HealthCheck(
            check_id=self._next_id(),
            platform=platform,
            check_type=CheckType.BLOCK,
            status=HealthStatus.BLOCKED,
            latency_ms=0,
            success=False,
            error=f"Blocked: {block_type}",
            details=details or {"block_type": block_type},
        )
        return self.report_check(check)

    def _update_health(self, platform: str) -> PlatformHealth:
        """Update platform health from recent checks.

        Args:
            platform: Platform to update.

        Returns:
            Updated PlatformHealth.
        """
        health = self._platforms[platform]
        checks = self._checks[platform]

        now = time.time()
        window_seconds = self.failure_window_minutes * 60

        # Filter recent checks
        recent = [c for c in checks if now - c.timestamp < window_seconds]

        if not recent:
            return health

        # Compute metrics
        successes = [c for c in recent if c.success]
        failures = [c for c in recent if not c.success]
        blocks = [c for c in recent if c.check_type == CheckType.BLOCK]

        health.success_rate = len(successes) / len(recent)
        health.error_rate = len(failures) / len(recent)
        health.block_risk = len(blocks) / max(1, len(recent))

        if successes:
            health.latency_ms = sum(c.latency_ms for c in successes) / len(successes)
        elif failures:
            health.latency_ms = sum(c.latency_ms for c in failures) / len(failures)

        health.last_check = recent[-1].timestamp

        # Update consecutive counters
        if recent[-1].success:
            health.consecutive_successes += 1
            health.consecutive_failures = 0
            health.last_success = recent[-1].timestamp
        else:
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            health.last_failure = recent[-1].timestamp

        # Track blocks
        if blocks:
            health.last_block = blocks[-1].timestamp

        # Compute composite health score
        health.health_score = self._compute_score(health)
        health.checks_count = len(checks)

        # Determine status
        if health.block_risk >= self.block_threshold:
            health.status = HealthStatus.BLOCKED
        elif health.consecutive_failures >= self.max_consecutive_failures:
            health.status = HealthStatus.DOWN
        elif health.health_score >= self.health_threshold:
            health.status = HealthStatus.HEALTHY
        elif health.health_score >= 40:
            health.status = HealthStatus.DEGRADED
        else:
            health.status = HealthStatus.UNSTABLE

        return health

    def _compute_score(self, health: PlatformHealth) -> float:
        """Compute composite health score (0-100).

        Score = success_rate * 40 + latency_score * 20 + block_safety * 30 + consecutive_bonus * 10

        Args:
            health: PlatformHealth to score.

        Returns:
            Composite score (0-100).
        """
        # Success rate component (0-40)
        success_score = health.success_rate * 40

        # Latency component (0-20): lower latency = higher score
        # Normalize: 0ms = 20, 5000ms = 0
        latency_score = max(0, 20 - health.latency_ms / 250)

        # Block safety component (0-30): no block risk = 30
        block_score = (1 - health.block_risk) * 30

        # Consecutive successes bonus (0-10)
        consec_score = min(10, health.consecutive_successes * 2)

        # Failure penalty
        failure_penalty = health.consecutive_failures * 5

        total = success_score + latency_score + block_score + consec_score - failure_penalty
        return max(0, min(100, total))

    def get_health(self, platform: str) -> PlatformHealth | None:
        """Get current health for a platform.

        Args:
            platform: Platform name.

        Returns:
            PlatformHealth or None if not monitored.
        """
        return self._platforms.get(platform)

    def get_all_health(self) -> dict[str, PlatformHealth]:
        """Get health for all monitored platforms.

        Returns:
            Dict of platform → PlatformHealth.
        """
        return dict(self._platforms)

    def compare_platforms(self) -> list[dict[str, Any]]:
        """Compare health across all platforms, sorted by score.

        Returns:
            List of platform health dicts, sorted by health_score descending.
        """
        results = []
        for platform, health in self._platforms.items():
            results.append(health.to_dict())

        results.sort(key=lambda r: -r.get("health_score", 0))
        return results

    def detect_degradation(self, min_score: float | None = None) -> list[str]:
        """Find platforms with degraded health.

        Args:
            min_score: Minimum score threshold (default: health_threshold).

        Returns:
            List of platform names with degraded health.
        """
        threshold = min_score or self.health_threshold
        return [
            p for p, h in self._platforms.items()
            if h.health_score < threshold
        ]

    def best_platform(self, platforms: list[str] | None = None) -> str | None:
        """Find the platform with best current health.

        Args:
            platforms: Optional subset of platforms to compare.

        Returns:
            Platform name with highest health score, or None.
        """
        candidates = platforms or list(self._platforms.keys())
        if not candidates:
            return None

        best = max(
            candidates,
            key=lambda p: self._platforms.get(p, PlatformHealth(platform=p)).health_score,
        )
        health = self._platforms.get(best)
        if health and health.is_available:
            return best
        return None

    def stats(self) -> dict[str, Any]:
        """Monitoring statistics.

        Returns:
            Dict with platform counts, average health, etc.
        """
        total = len(self._platforms)
        healthy = sum(1 for h in self._platforms.values() if h.status == HealthStatus.HEALTHY)
        degraded = sum(1 for h in self._platforms.values() if h.status == HealthStatus.DEGRADED)
        blocked = sum(1 for h in self._platforms.values() if h.status == HealthStatus.BLOCKED)
        down = sum(1 for h in self._platforms.values() if h.status == HealthStatus.DOWN)

        avg_score = sum(h.health_score for h in self._platforms.values()) / total if total else 0
        avg_latency = sum(h.latency_ms for h in self._platforms.values()) / total if total else 0

        return {
            "monitored_platforms": total,
            "healthy": healthy,
            "degraded": degraded,
            "blocked": blocked,
            "down": down,
            "unknown": total - healthy - degraded - blocked - down,
            "avg_health_score": round(avg_score, 1),
            "avg_latency_ms": round(avg_latency, 1),
        }
