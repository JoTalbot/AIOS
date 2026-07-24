"""Quantum Advantage Analysis for AIOS v10.10.0.

Quantum advantage analysis: classical/quantum time comparison,
speedup estimation, crossover point detection, complexity class
analysis, benchmark suites, noise impact estimation, and
resource requirement tracking.

Classes:
    BenchmarkEntry — single benchmark measurement
    QuantumAdvantageAnalyzer — full analyzer
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkEntry:
    """Single benchmark measurement."""

    def __init__(
        self, name: str, classical_time: float, quantum_time: float, problem_size: int
    ) -> None:
        self.name = name
        self.classical_time = classical_time
        self.quantum_time = quantum_time
        self.problem_size = problem_size
        self.speedup = (
            classical_time / quantum_time if quantum_time > 0 else float("inf")
        )


class QuantumAdvantageAnalyzer:
    """Analyzes when quantum algorithms provide advantage."""

    def __init__(self) -> None:
        self.benchmarks: dict[str, dict[str, Any]] = {}

    def compare(
        self, classical_time: float, quantum_time: float, problem_size: int
    ) -> dict[str, Any]:
        """Compare classical vs quantum (backward-compatible)."""
        speedup = classical_time / quantum_time if quantum_time > 0 else float("inf")
        advantage = speedup > 1 and problem_size > 20
        BenchmarkEntry("comparison", classical_time, quantum_time, problem_size)
        self.benchmarks[f"bench_{len(self.benchmarks)}"] = {
            "classical_time": classical_time,
            "quantum_time": quantum_time,
            "speedup": round(speedup, 2),
            "problem_size": problem_size,
        }
        return {
            "speedup": round(speedup, 2),
            "quantum_advantage": advantage,
            "crossover_point": 20 if advantage else None,
        }

    def complexity_class(self, algorithm: str) -> dict[str, Any]:
        """Classify quantum algorithm complexity class."""
        classes = {
            "grover": {
                "classical": "O(N)",
                "quantum": "O(N^0.5)",
                "speedup": "quadratic",
            },
            "shor": {
                "classical": "O(N^3)",
                "quantum": "O(log(N)^3)",
                "speedup": "exponential",
            },
            "vqe": {
                "classical": "O(2^n)",
                "quantum": "O(n^k)",
                "speedup": "exponential",
            },
            "qaoa": {
                "classical": "O(2^n)",
                "quantum": "O(poly(n))",
                "speedup": "exponential",
            },
            "hhl": {
                "classical": "O(N^3)",
                "quantum": "O(log(N)^2)",
                "speedup": "exponential",
            },
            "qft": {
                "classical": "O(N^2)",
                "quantum": "O(N*log(N))",
                "speedup": "quadratic",
            },
        }
        return classes.get(
            algorithm,
            {"classical": "unknown", "quantum": "unknown", "speedup": "unknown"},
        )

    def estimate_crossover(
        self,
        classical_growth: str = "exponential",
        quantum_growth: str = "polynomial",
        base_rate: float = 1.0,
    ) -> dict[str, Any]:
        """Estimate crossover point where quantum becomes faster."""
        if classical_growth == "exponential" and quantum_growth == "polynomial":
            crossover = 25  # Typical for exponential vs polynomial
        elif classical_growth == "quadratic" and quantum_growth == "linear":
            crossover = 50
        else:
            crossover = 30  # Default estimate
        return {
            "crossover_size": crossover,
            "classical_growth": classical_growth,
            "quantum_growth": quantum_growth,
            "advantage_after_crossover": True,
        }

    def noise_impact(self, noise_rate: float, problem_size: int) -> dict[str, Any]:
        """Estimate impact of noise on quantum advantage."""
        # Noise reduces effective speedup
        effective_speedup = max(1, (problem_size / 20) * (1 - noise_rate * 10))
        return {
            "noise_rate": noise_rate,
            "effective_speedup": round(effective_speedup, 2),
            "advantage_lost": effective_speedup < 1.5,
            "minimum_noise_tolerance": round(1 / (problem_size / 20), 4),
        }

    def resource_requirements(
        self, algorithm: str, problem_size: int
    ) -> dict[str, Any]:
        """Estimate quantum resource requirements."""
        qubits_needed = {
            "shor": int(problem_size * 2),
            "grover": math.ceil(math.sqrt(problem_size)),
            "vqe": int(problem_size),
            "qaoa": int(problem_size),
        }
        n = qubits_needed.get(algorithm, problem_size)
        return {
            "algorithm": algorithm,
            "qubits_needed": n,
            "circuit_depth": n * 10,
            "estimated_time_ms": round(n * 0.1, 2),
            "feasibility": n < 1000,
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {"benchmarks": len(self.benchmarks)}
