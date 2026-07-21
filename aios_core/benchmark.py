"""Benchmarking Suite for AIOS"""

import time
from typing import Callable, Dict


class Benchmark:
    """Performance benchmarking tool."""

    def __init__(self):
        self.results: Dict[str, Dict] = {}

    def run(self, name: str, func: Callable, iterations: int = 1000, **kwargs):
        start = time.perf_counter()
        for _ in range(iterations):
            func(**kwargs)
        duration = time.perf_counter() - start
        self.results[name] = {
            "iterations": iterations,
            "total_seconds": round(duration, 4),
            "ops_per_second": round(iterations / duration, 2)
        }
        return self.results[name]

    def compare(self, name1: str, name2: str) -> str:
        r1 = self.results.get(name1, {})
        r2 = self.results.get(name2, {})
        if not r1 or not r2:
            return "Insufficient data"
        return f"{name1} is {r1.get('ops_per_second', 0) / max(r2.get('ops_per_second', 1), 1):.2f}x faster than {name2}"

    def stats(self) -> dict:
        return {"benchmarks": len(self.results)}