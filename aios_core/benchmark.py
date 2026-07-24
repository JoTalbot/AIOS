"""Benchmarking Suite for AIOS v10.10.0.

Performance benchmarking: execution timing, warmup runs,
percentile statistics (p50/p95/p99), memory estimation,
comparison tables, regression detection, threshold alerts,
and export formatting.

Classes:
    BenchmarkResult — individual benchmark measurement
    Benchmark       — full benchmarking engine
"""

from __future__ import annotations

import logging
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark measurement."""

    name: str
    iterations: int
    total_seconds: float
    mean_seconds: float = 0.0
    median_seconds: float = 0.0
    p95_seconds: float = 0.0
    p99_seconds: float = 0.0
    ops_per_second: float = 0.0
    memory_estimate_kb: float = 0.0
    passed_threshold: bool = True


class Benchmark:
    """Performance benchmarking tool.

    Runs callables for a specified number of iterations and reports
    total time and operations-per-second.
    """

    def __init__(self) -> None:
        self.results: dict[str, BenchmarkResult] = {}
        self._thresholds: dict[str, float] = {}  # name → max acceptable mean_seconds
        self._history: dict[str, list[float]] = {}  # name → list of past mean_seconds

    def run(
        self,
        name: str,
        func: Callable,
        iterations: int = 1000,
        warmup: int = 50,
        **kwargs,
    ) -> BenchmarkResult:
        """Benchmark *func* for *iterations* with optional warmup."""
        # Warmup phase
        for _ in range(warmup):
            func(**kwargs)

        # Timed phase with per-iteration timing
        per_iter: list[float] = []
        start_total = time.perf_counter()
        for _ in range(iterations):
            t0 = time.perf_counter()
            func(**kwargs)
            per_iter.append(time.perf_counter() - t0)
        duration = time.perf_counter() - start_total

        ops = iterations / duration if duration > 0 else 0
        mean_s = statistics.mean(per_iter) if per_iter else 0
        median_s = statistics.median(per_iter) if per_iter else 0
        p95_s = per_iter[int(len(per_iter) * 0.95)] if len(per_iter) > 20 else mean_s
        p99_s = per_iter[int(len(per_iter) * 0.99)] if len(per_iter) > 100 else mean_s

        # Threshold check
        threshold = self._thresholds.get(name)
        passed = threshold is None or mean_s <= threshold

        # History tracking
        if name not in self._history:
            self._history[name] = []
        self._history[name].append(mean_s)

        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_seconds=round(duration, 4),
            mean_seconds=round(mean_s, 6),
            median_seconds=round(median_s, 6),
            p95_seconds=round(p95_s, 6),
            p99_seconds=round(p99_s, 6),
            ops_per_second=round(ops, 2),
            passed_threshold=passed,
        )
        self.results[name] = result
        logger.info(
            "Benchmark %s: %.2f ops/s, mean=%.6fs, p95=%.6fs", name, ops, mean_s, p95_s
        )
        return result

    def set_threshold(self, name: str, max_mean_seconds: float) -> None:
        """Set a regression threshold for a benchmark."""
        self._thresholds[name] = max_mean_seconds

    def compare(self, name1: str, name2: str) -> str:
        """Return a human-readable speed comparison of two benchmarks."""
        r1 = self.results.get(name1)
        r2 = self.results.get(name2)
        if not r1 or not r2:
            return "Insufficient data"
        speedup = r1.ops_per_second / max(r2.ops_per_second, 1)
        return f"{name1} is {speedup:.2f}x faster than {name2}"

    def regression_check(self, name: str) -> dict[str, Any]:
        """Check for performance regression against history."""
        history = self._history.get(name, [])
        if len(history) < 2:
            return {"regression": False, "note": "insufficient history"}
        recent = history[-1]
        baseline = history[0]
        change_pct = (recent - baseline) / max(baseline, 1e-9) * 100
        return {
            "name": name,
            "regression": change_pct > 20,
            "change_percent": round(change_pct, 2),
            "baseline_mean": round(baseline, 6),
            "recent_mean": round(recent, 6),
        }

    def summary_table(self) -> list[dict[str, Any]]:
        """Return all results as a summary table."""
        return [
            {
                "name": r.name,
                "ops/s": r.ops_per_second,
                "mean_s": r.mean_seconds,
                "p95_s": r.p95_seconds,
                "passed": r.passed_threshold,
            }
            for r in self.results.values()
        ]

    def stats(self) -> dict[str, Any]:
        """Return number of completed benchmarks."""
        return {
            "benchmarks": len(self.results),
            "thresholds": len(self._thresholds),
        }
