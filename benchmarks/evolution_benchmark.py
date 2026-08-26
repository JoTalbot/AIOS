"""Benchmark evolution progress in AIOS."""


class EvolutionBenchmark:
    def __init__(self):
        self.history = []

    def record(self, metrics):
        self.history.append(metrics)

    def latest(self):
        return self.history[-1] if self.history else None

    def count(self):
        return len(self.history)
