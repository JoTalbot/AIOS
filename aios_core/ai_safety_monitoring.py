"""Real-time AI Safety Monitoring for AIOS v10.11.0.

Safety monitoring: metric recording, threshold alerts,
status tracking, trend analysis, metric history,
escalation rules, and monitoring reports.

Classes:
    SafetyMonitor — full monitoring engine
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["SafetyMonitor"]


class SafetyMonitor:
    """Real-time safety monitoring system (backward-compatible)."""

    def __init__(self) -> None:
        self.metrics: dict[str, list[float]] = {}
        self.alerts: list[dict[str, Any]] = []
        self.thresholds: dict[str, float] = {
            "harm_score": 0.3,
            "bias_score": 0.4,
            "deception_score": 0.2,
        }
        self._escalation_rules: list[dict[str, Any]] = []
        self._reports: list[dict[str, Any]] = []

    def record_metric(self, metric: str, value: float) -> None:
        """Record metric (backward-compatible)."""
        if metric not in self.metrics:
            self.metrics[metric] = []
        self.metrics[metric].append(value)
        # Keep last 1000 values
        if len(self.metrics[metric]) > 1000:
            self.metrics[metric] = self.metrics[metric][-1000:]
        # Check threshold
        if metric in self.thresholds and value > self.thresholds[metric]:
            self.alerts.append({
                "metric": metric,
                "value": value,
                "threshold": self.thresholds[metric],
                "timestamp": time.time(),
            })

    def get_status(self) -> dict[str, Any]:
        """Get current status (backward-compatible)."""
        latest_metrics = {k: v[-1] if v else 0 for k, v in self.metrics.items()}
        return {
            "metrics": latest_metrics,
            "alerts": len(self.alerts),
            "status": "healthy" if not self.alerts else "warning",
        }

    def trend_analysis(self, metric: str, window: int = 10) -> dict[str, Any]:
        """Analyze trend for a metric."""
        data = self.metrics.get(metric, [])
        if len(data) < window:
            return {"metric": metric, "trend": "insufficient_data", "points": len(data)}
        recent = data[-window:]
        mean = sum(recent) / len(recent)
        if len(recent) >= 2:
            slope = (recent[-1] - recent[0]) / len(recent)
        else:
            slope = 0.0
        trend = "improving" if slope < -0.01 else ("declining" if slope > 0.01 else "stable")
        return {"metric": metric, "trend": trend, "mean": round(mean, 3), "slope": round(slope, 3)}

    def add_escalation_rule(self, metric: str, threshold: float, action: str = "notify") -> None:
        """Add escalation rule."""
        self._escalation_rules.append({"metric": metric, "threshold": threshold, "action": action})

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive monitoring report."""
        all_metrics: dict[str, Any] = {}
        for metric, values in self.metrics.items():
            if values:
                all_metrics[metric] = {
                    "latest": round(values[-1], 3),
                    "mean": round(sum(values) / len(values), 3),
                    "min": round(min(values), 3),
                    "max": round(max(values), 3),
                    "trend": self.trend_analysis(metric).get("trend", "unknown"),
                }
        report = {
            "timestamp": time.time(),
            "metrics_summary": all_metrics,
            "alerts_count": len(self.alerts),
            "status": "healthy" if not self.alerts else "warning",
        }
        self._reports.append(report)
        return report

    def check_escalation(self) -> list[dict[str, Any]]:
        """Check if any escalation rules are triggered."""
        triggered: list[dict[str, Any]] = []
        for rule in self._escalation_rules:
            values = self.metrics.get(rule["metric"], [])
            if values and values[-1] > rule["threshold"]:
                triggered.append(rule)
        return triggered

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "metrics_tracked": len(self.metrics),
            "alerts": len(self.alerts),
            "total_data_points": sum(len(v) for v in self.metrics.values()),
            "escalation_rules": len(self._escalation_rules),
        }
