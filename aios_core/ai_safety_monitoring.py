"""Real-time AI Safety Monitoring"""

import time
from typing import Dict, List

__all__ = ["SafetyMonitor"]


class SafetyMonitor:
    """Real-time safety monitoring system."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.alerts: List[Dict] = []
        self.thresholds: Dict[str, float] = {
            "harm_score": 0.3,
            "bias_score": 0.4,
            "deception_score": 0.2,
        }

    def record_metric(self, metric: str, value: float) -> None:
        """Execute record metric."""
        if metric not in self.metrics:
            self.metrics[metric] = []
        self.metrics[metric].append(value)

        if metric in self.thresholds and value > self.thresholds[metric]:
            self.alerts.append(
                {
                    "metric": metric,
                    "value": value,
                    "threshold": self.thresholds[metric],
                    "timestamp": time.time(),
                }
            )

    def get_status(self) -> Dict:
        """Execute get status."""
        return {
            "metrics": {k: v[-1] if v else 0 for k, v in self.metrics.items()},
            "alerts": len(self.alerts),
            "status": "healthy" if not self.alerts else "warning",
        }

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"metrics_tracked": len(self.metrics), "alerts": len(self.alerts)}
