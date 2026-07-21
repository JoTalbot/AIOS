"""Anomaly Detection for AIOS"""

from typing import List, Dict
import statistics


class AnomalyDetector:
    """Simple statistical anomaly detector."""

    def __init__(self, threshold: float = 2.0):
        self.threshold = threshold
        self.history: List[float] = []

    def add_value(self, value: float):
        self.history.append(value)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    def is_anomaly(self, value: float) -> bool:
        if len(self.history) < 10:
            return False
        mean = statistics.mean(self.history)
        stdev = statistics.stdev(self.history) if len(self.history) > 1 else 0
        if stdev == 0:
            return False
        z_score = abs((value - mean) / stdev)
        return z_score > self.threshold

    def stats(self) -> dict:
        return {"samples": len(self.history), "threshold": self.threshold}