"""Lightweight anomaly detection for Digital Twin state snapshots."""

from statistics import mean
from typing import Iterable, List


class AnomalyDetector:
    def __init__(self, threshold: float = 2.0):
        self.threshold = threshold

    def detect(self, values: Iterable[float]) -> List[float]:
        values = list(values)
        if len(values) < 2:
            return []
        baseline = mean(values)
        return [v for v in values if abs(v - baseline) > self.threshold]
