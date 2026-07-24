"""Benchmarks CI thresholds — regression gate for performance tests.

Defines maximum allowed execution time for key operations:
- Core import time
- Storage operations (save_ads, get_ads, price_history)
- Rate limiter operations (is_allowed, reset)
- Vector search (build_index, search)
- Cross-platform comparator (compare)

Thresholds are enforced in CI via pytest-timeout and pytest-benchmark.
If any benchmark exceeds its threshold, the CI job fails (blocking).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThresholdConfig:
    """Performance threshold for a named benchmark."""

    name: str
    max_ms: float           # Maximum allowed time in milliseconds
    min_rounds: int = 5     # Minimum benchmark rounds
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "name": self.name,
            "max_ms": self.max_ms,
            "min_rounds": self.min_rounds,
            "description": self.description,
        }


# Default thresholds (can be overridden via CI env vars)
THRESHOLDS: list[ThresholdConfig] = [
    ThresholdConfig(
        name="core_import",
        max_ms=500,
        description="Total time to import aios_core package",
    ),
    ThresholdConfig(
        name="storage_save_ads_100",
        max_ms=50,
        description="Save 100 ads to SQLite (in-memory)",
    ),
    ThresholdConfig(
        name="storage_get_ads_1000",
        max_ms=30,
        description="Get 1000 ads from SQLite",
    ),
    ThresholdConfig(
        name="storage_price_history",
        max_ms=10,
        description="Get price history for a single product",
    ),
    ThresholdConfig(
        name="rate_limiter_is_allowed",
        max_ms=1,
        description="Single RateLimiter.is_allowed() check",
    ),
    ThresholdConfig(
        name="rate_limiter_reset",
        max_ms=5,
        description="RateLimiter.reset() for all keys",
    ),
    ThresholdConfig(
        name="vector_search_build_index_1000",
        max_ms=500,
        description="Build TF-IDF index for 1000 products",
    ),
    ThresholdConfig(
        name="vector_search_query",
        max_ms=50,
        description="Search query against 1000-product index",
    ),
    ThresholdConfig(
        name="cross_platform_compare_500",
        max_ms=200,
        description="Compare 500 products across 2 platforms",
    ),
    ThresholdConfig(
        name="autowatch_cycle_no_collect",
        max_ms=100,
        description="AutoWatch cycle (no collect, just analysis)",
    ),
]


def get_threshold(name: str) -> ThresholdConfig | None:
    """Get threshold config by name.

    Args:
        name: Benchmark name.

    Returns:
        ThresholdConfig or None if not found.
    """
    for t in THRESHOLDS:
        if t.name == name:
            return t
    return None


def check_threshold(name: str, actual_ms: float) -> dict[str, object]:
    """Check if a benchmark result passes its threshold.

    Args:
        name: Benchmark name.
        actual_ms: Actual execution time in milliseconds.

    Returns:
        Dict with pass/fail status and threshold details.
    """
    threshold = get_threshold(name)
    if threshold is None:
        return {"name": name, "status": "unknown", "actual_ms": actual_ms, "threshold_ms": None}

    passed = actual_ms <= threshold.max_ms
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "actual_ms": round(actual_ms, 2),
        "threshold_ms": threshold.max_ms,
        "over_pct": round(((actual_ms - threshold.max_ms) / threshold.max_ms) * 100, 2) if not passed else 0,
        "description": threshold.description,
    }


def all_thresholds() -> list[dict[str, object]]:
    """Return all threshold configs as dicts."""
    return [t.to_dict() for t in THRESHOLDS]
