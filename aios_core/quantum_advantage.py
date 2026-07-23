"""Quantum Advantage Analysis for AIOS"""

from typing import Dict


class QuantumAdvantageAnalyzer:
    """Analyzes when quantum algorithms provide advantage."""

    def __init__(self):
        self.benchmarks: dict[str, dict] = {}

    def compare(self, classical_time: float, quantum_time: float, problem_size: int) -> Dict:
        """Execute compare."""
        speedup = classical_time / quantum_time if quantum_time > 0 else float("inf")
        advantage = speedup > 1 and problem_size > 20
        return {
            "speedup": round(speedup, 2),
            "quantum_advantage": advantage,
            "crossover_point": 20 if advantage else None,
        }

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"benchmarks": len(self.benchmarks)}
