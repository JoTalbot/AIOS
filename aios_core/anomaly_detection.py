"""Anomaly Detection Engine for AIOS Executive Layer.

Provides statistical and Z-Score / IQR multi-variate outlier detection across
execution metrics (latency, memory, error rate, failure count).
"""

import math
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple


class AnomalyDetector:
    """Multi-variate Anomaly Detection Engine for agent runtime metrics."""

    def __init__(
        self,
        z_threshold: float = 2.5,
        iqr_multiplier: float = 1.5,
        window_size: int = 1000,
    ):
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.window_size = window_size
        self.histories: Dict[str, list[float]] = {}
        self.anomaly_log: List[dict[str, Any]] = []

    def add_value(self, metric_name: str, value: float) -> None:
        """Record a single metric sample into historical window."""
        if metric_name not in self.histories:
            self.histories[metric_name] = []

        history = self.histories[metric_name]
        history.append(value)
        if len(history) > self.window_size:
            self.histories[metric_name] = history[-self.window_size :]

    def is_anomaly(self, value: float, metric_name: str | None = None) -> bool:
        """Check if a new metric value is an outlier based on historical window Z-Score."""
        target_name = metric_name or "default"
        if target_name not in self.histories:
            self.add_value(target_name, value)
            return False

        history = self.histories[target_name]
        if len(history) < 5:
            self.add_value(target_name, value)
            return False

        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0.0

        if stdev == 0.0:
            self.add_value(target_name, value)
            return False

        z_score = abs((value - mean) / stdev)
        is_anomalous = z_score > self.z_threshold

        if is_anomalous:
            self.anomaly_log.append(
                {
                    "metric": target_name,
                    "value": value,
                    "mean": round(mean, 4),
                    "stdev": round(stdev, 4),
                    "z_score": round(z_score, 4),
                    "timestamp": time.time(),
                }
            )

        self.add_value(target_name, value)
        return is_anomalous

    def is_iqr_anomaly(self, value: float, metric_name: str) -> bool:
        """Check for outliers using Interquartile Range (IQR) method."""
        if metric_name not in self.histories:
            self.add_value(metric_name, value)
            return False

        history = sorted(self.histories[metric_name])
        if len(history) < 10:
            self.add_value(metric_name, value)
            return False

        q1 = numpy_percentile(history, 25)
        q3 = numpy_percentile(history, 75)
        iqr = q3 - q1

        lower_bound = q1 - (self.iqr_multiplier * iqr)
        upper_bound = q3 + (self.iqr_multiplier * iqr)

        is_anomalous = value < lower_bound or value > upper_bound
        self.add_value(metric_name, value)
        return is_anomalous

    def detect_multivariate(self, sample: dict[str, float]) -> dict[str, Any]:
        """Detect anomalies across multiple metrics simultaneously."""
        results = {}
        any_anomalous = False

        for name, val in sample.items():
            anomalous = self.is_anomaly(val, metric_name=name)
            results[name] = {"value": val, "anomalous": anomalous}
            if anomalous:
                any_anomalous = True

        return {
            "overall_anomaly": any_anomalous,
            "metrics": results,
            "timestamp": time.time(),
        }

    def stats(self) -> dict[str, Any]:
        """Summary of anomaly detection engine activity."""
        return {
            "monitored_metrics": len(self.histories),
            "total_anomalies_logged": len(self.anomaly_log),
            "z_threshold": self.z_threshold,
            "samples_window": {k: len(v) for k, v in self.histories.items()},
        }


def numpy_percentile(data: list[float], percentile: float) -> float:
    """Compute percentile from sorted array."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return d0 + d1
