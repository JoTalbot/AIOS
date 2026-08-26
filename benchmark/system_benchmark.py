from dataclasses import dataclass
from typing import Dict


@dataclass
class BenchmarkResult:
    name: str
    score: float


class SystemBenchmark:
    def __init__(self):
        self.results: Dict[str, BenchmarkResult] = {}

    def record(self, name: str, score: float) -> BenchmarkResult:
        result = BenchmarkResult(name=name, score=score)
        self.results[name] = result
        return result

    def best(self):
        if not self.results:
            return None
        return max(self.results.values(), key=lambda item: item.score)
