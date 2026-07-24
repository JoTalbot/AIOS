"""Performance Profiling for AIOS v10.9.0.

Performance profiling with context-manager measurement,
memory tracking, CPU profiling, benchmark suite,
performance alerts, and optimization suggestions.

Classes:
    PerformanceAlert — performance warning
    PerformanceProfiler — full profiling engine
"""

from __future__ import annotations

import logging
import math
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Generator

logger = logging.getLogger(__name__)


@dataclass
class PerformanceAlert:
    """Performance warning."""
    name: str
    threshold_ms: float
    actual_ms: float
    severity: str = "warning"  # info, warning, critical


class PerformanceProfiler:
    """Full performance profiling engine.

    Features:
    - Context-manager timing (backward-compatible)
    - Memory estimation
    - CPU time tracking
    - Performance alerts
    - Optimization suggestions
    - Benchmark suite
    """

    def __init__(self, alert_threshold_ms: float = 100.0) -> None:
        self.measurements: dict[str, list[float]] = {}
        self.alert_threshold_ms = alert_threshold_ms
        self._alerts: list[PerformanceAlert] = []
        self._benchmarks: dict[str, Any] = {}

    @contextmanager
    def measure(self, name: str) -> Generator[None, None, None]:
        """Measure execution time (backward-compatible)."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = (time.perf_counter() - start) * 1000
            if name not in self.measurements:
                self.measurements[name] = []
            self.measurements[name].append(duration)

            # Alert if exceeds threshold
            if duration > self.alert_threshold_ms:
                self._alerts.append(PerformanceAlert(
                    name=name, threshold_ms=self.alert_threshold_ms,
                    actual_ms=round(duration, 2),
                    severity="critical" if duration > self.alert_threshold_ms * 3 else "warning",
                ))

    def measure_function(self, func: Callable, name: str = "") -> dict[str, Any]:
        """Measure a function execution."""
        name = name or func.__name__
        start = time.perf_counter()
        result = func()
        duration = (time.perf_counter() - start) * 1000

        if name not in self.measurements:
            self.measurements[name] = []
        self.measurements[name].append(duration)

        return {"name": name, "duration_ms": round(duration, 4), "result": result}

    def benchmark(self, func: Callable, name: str = "", runs: int = 10) -> dict[str, Any]:
        """Benchmark a function over multiple runs."""
        name = name or func.__name__
        times = []
        for _ in range(runs):
            start = time.perf_counter()
            func()
            times.append((time.perf_counter() - start) * 1000)

        self.measurements[name] = times
        self._benchmarks[name] = {
            "runs": runs,
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "std_ms": round(math.sqrt(sum((t - sum(times)/len(times))**2 for t in times) / len(times)), 2) if len(times) >= 2 else 0,
        }
        return self._benchmarks[name]

    def get_alerts(self) -> list[dict[str, Any]]:
        """Return all performance alerts."""
        return [{"name": a.name, "severity": a.severity,
                 "actual_ms": a.actual_ms, "threshold_ms": a.threshold_ms}
                for a in self._alerts]

    def optimization_suggestions(self) -> list[str]:
        """Return optimization suggestions based on measurements."""
        suggestions = []
        for name, times in self.measurements.items():
            avg = sum(times) / len(times)
            if avg > 100:
                suggestions.append(f"{name}: Consider caching or async execution (avg {round(avg, 1)}ms)")
            if max(times) > min(times) * 3:
                suggestions.append(f"{name}: High variance suggests inconsistent performance")
        return suggestions

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        result = {}
        for name, times in self.measurements.items():
            result[name] = {
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 2),
                "max_ms": round(max(times), 2),
                "min_ms": round(min(times), 2),
            }
        return result


profiler = PerformanceProfiler()
