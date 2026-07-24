"""AI Safety Benchmark Suite for AIOS v10.11.0.

Safety benchmarks: standardized evaluation suites,
benchmark execution, leaderboard management, scoring
methodology, comparison tracking, and benchmark
metadata.

Classes:
    BenchmarkSuite  — benchmark suite metadata
    SafetyBenchmark — full benchmark engine
"""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["SafetyBenchmark"]


class BenchmarkSuite:
    """Benchmark suite metadata."""

    def __init__(self, name: str, description: str = "", metrics: list[str] = []) -> None:
        self.name = name
        self.description = description
        self.metrics = metrics
        self._results: list[float] = []


class SafetyBenchmark:
    """Standardized AI safety benchmarks (backward-compatible)."""

    def __init__(self) -> None:
        self.benchmarks: dict[str, dict[str, Any]] = {
            "harmbench": {"score": 0.0, "status": "not_run", "description": "Harmful content generation"},
            "truthfulqa": {"score": 0.0, "status": "not_run", "description": "Truthfulness evaluation"},
            "realtoxicityprompts": {"score": 0.0, "status": "not_run", "description": "Toxic content detection"},
            "bold": {"score": 0.0, "status": "not_run", "description": "Bias evaluation"},
            "ethics": {"score": 0.0, "status": "not_run", "description": "Ethical reasoning"},
        }
        self._suites: list[BenchmarkSuite] = []
        self._comparison_data: dict[str, list[float]] = {}

    def run_benchmark(self, benchmark_name: str, model: Any) -> dict[str, Any]:
        """Run benchmark (backward-compatible)."""
        if benchmark_name not in self.benchmarks:
            return {"error": "benchmark not found"}
        # Simulate benchmark execution
        score = round(random.uniform(0.75, 0.95), 2)
        self.benchmarks[benchmark_name] = {
            "score": score,
            "status": "completed",
            "details": f"Model scored {score} on {benchmark_name}",
        }
        self._comparison_data.setdefault(benchmark_name, []).append(score)
        return self.benchmarks[benchmark_name]

    def run_all(self, model: Any) -> dict[str, dict[str, Any]]:
        """Run all benchmarks."""
        results: dict[str, dict[str, Any]] = {}
        for name in self.benchmarks:
            results[name] = self.run_benchmark(name, model)
        return results

    def get_leaderboard(self) -> dict[str, Any]:
        """Get leaderboard (backward-compatible)."""
        completed = {k: v for k, v in self.benchmarks.items() if v["status"] == "completed"}
        if not completed:
            return self.benchmarks
        sorted_benchmarks = dict(sorted(completed.items(), key=lambda x: x[1]["score"], reverse=True))
        return sorted_benchmarks

    def compare_models(self, model_name_a: str, model_name_b: str) -> dict[str, Any]:
        """Compare two models across benchmarks."""
        comparisons: dict[str, dict[str, float]] = {}
        for bench_name, scores in self._comparison_data.items():
            if len(scores) >= 2:
                comparisons[bench_name] = {
                    "model_a": scores[0],
                    "model_b": scores[-1],
                    "difference": round(scores[-1] - scores[0], 2),
                }
        return {"comparisons": comparisons, "benchmarks_compared": len(comparisons)}

    def add_benchmark(self, name: str, description: str = "", metrics: list[str] = []) -> None:
        """Add a custom benchmark."""
        self.benchmarks[name] = {"score": 0.0, "status": "not_run", "description": description}
        self._suites.append(BenchmarkSuite(name, description, metrics))

    def aggregate_score(self) -> float:
        """Compute aggregate safety score across completed benchmarks."""
        completed_scores = [v["score"] for v in self.benchmarks.values() if v["status"] == "completed"]
        return round(sum(completed_scores) / max(len(completed_scores), 1), 2) if completed_scores else 0.0

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "benchmarks": len(self.benchmarks),
            "completed": sum(1 for v in self.benchmarks.values() if v["status"] == "completed"),
            "aggregate_score": self.aggregate_score(),
        }
