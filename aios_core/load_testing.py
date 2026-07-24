"""Load Testing Framework for AIOS v10.12.0.

Load testing: concurrent execution, ramp-up strategies,
latency distribution, percentile reporting, throughput
measurement, comparison, and load profile management.

Classes:
    LoadProfile    — load test configuration
    LoadTester     — full load testing engine
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["LoadTester"]


class LoadProfile:
    """Load test configuration."""

    def __init__(
        self,
        name: str,
        concurrent_users: int = 10,
        duration_seconds: int = 30,
        ramp_up_seconds: int = 5,
    ) -> None:
        self.name = name
        self.concurrent_users = concurrent_users
        self.duration_seconds = duration_seconds
        self.ramp_up_seconds = ramp_up_seconds


class LoadTester:
    """Concurrent load tester (backward-compatible)."""

    def __init__(self) -> None:
        self.results: list[float] = []
        self._profiles: list[LoadProfile] = []
        self._errors: int = 0

    def run(
        self, func: Callable, concurrent_users: int = 10, duration_seconds: int = 30
    ) -> dict[str, Any]:
        """Run load test (backward-compatible + enhanced)."""
        self.results = []
        self._errors = 0
        start_time = time.time()

        def worker() -> None:
            while time.time() - start_time < duration_seconds:
                try:
                    t0 = time.perf_counter()
                    func()
                    latency = (time.perf_counter() - t0) * 1000
                    self.results.append(latency)
                except Exception:
                    self._errors += 1

        threads = [threading.Thread(target=worker) for _ in range(concurrent_users)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if not self.results:
            return {"error": "No successful requests"}

        return {
            "requests": len(self.results),
            "avg_latency_ms": round(sum(self.results) / len(self.results), 2),
            "max_latency_ms": round(max(self.results), 2),
            "min_latency_ms": round(min(self.results), 2),
            "rps": round(len(self.results) / duration_seconds, 2),
            "p50_ms": round(sorted(self.results)[len(self.results) // 2], 2),
            "p95_ms": round(sorted(self.results)[int(len(self.results) * 0.95)], 2),
            "p99_ms": round(sorted(self.results)[int(len(self.results) * 0.99)], 2),
            "errors": self._errors,
            "error_rate": round(
                self._errors / max(self._errors + len(self.results), 1), 4
            ),
        }

    def run_with_ramp_up(self, func: Callable, profile: LoadProfile) -> dict[str, Any]:
        """Run load test with ramp-up phase."""
        self.results = []
        self._errors = 0
        start_time = time.time()
        active_threads: list[threading.Thread] = []

        # Ramp-up: start threads gradually
        for i in range(profile.concurrent_users):
            ramp_delay = (i / profile.concurrent_users) * profile.ramp_up_seconds
            time.sleep(ramp_delay)

            def worker() -> None:
                while time.time() - start_time < profile.duration_seconds:
                    try:
                        t0 = time.perf_counter()
                        func()
                        latency = (time.perf_counter() - t0) * 1000
                        self.results.append(latency)
                    except Exception:
                        self._errors += 1

            t = threading.Thread(target=worker)
            active_threads.append(t)
            t.start()

        for t in active_threads:
            t.join()

        if not self.results:
            return {"error": "No successful requests"}

        return {
            "profile": profile.name,
            "concurrent_users": profile.concurrent_users,
            "ramp_up_seconds": profile.ramp_up_seconds,
            "duration_seconds": profile.duration_seconds,
            "total_requests": len(self.results),
            "avg_latency_ms": round(sum(self.results) / len(self.results), 2),
            "rps": round(len(self.results) / profile.duration_seconds, 2),
            "p95_ms": round(sorted(self.results)[int(len(self.results) * 0.95)], 2),
            "errors": self._errors,
        }

    def compare_profiles(
        self, func: Callable, profiles: list[LoadProfile]
    ) -> list[dict[str, Any]]:
        """Compare different load profiles."""
        comparisons: list[dict[str, Any]] = []
        for profile in profiles:
            result = self.run_with_ramp_up(func, profile)
            comparisons.append(result)
        return comparisons

    def latency_histogram(self, bins: int = 10) -> dict[str, Any]:
        """Generate latency histogram."""
        if not self.results:
            return {"bins": bins, "data": []}
        min_lat = min(self.results)
        max_lat = max(self.results)
        bin_width = (max_lat - min_lat) / bins
        histogram: dict[str, int] = {}
        for i in range(bins):
            lower = min_lat + i * bin_width
            upper = lower + bin_width
            key = f"{round(lower, 0)}-{round(upper, 0)}ms"
            count = sum(1 for r in self.results if lower <= r < upper)
            histogram[key] = count
        return {"bins": bins, "histogram": histogram, "total": len(self.results)}

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "tests_run": len(self.results),
            "profiles": len(self._profiles),
            "errors": self._errors,
        }
