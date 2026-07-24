"""AI Safety Dashboard for AIOS v10.11.0.

Safety dashboard: real-time safety metric monitoring,
incident tracking, safety score calculation, trend
visualization, alert management, and status reporting.

Classes:
    SafetyDashboard — full safety dashboard engine
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["SafetyDashboard"]


class SafetyDashboard:
    """Real-time safety monitoring dashboard (backward-compatible)."""

    def __init__(self) -> None:
        self.metrics: dict[str, float] = {}
        self.incidents: list[dict[str, Any]] = []
        self.safety_score: float = 1.0
        self._metric_history: dict[str, list[float]] = {}
        self._alerts: list[dict[str, Any]] = []
        self._alert_thresholds: dict[str, float] = {"harm": 0.3, "bias": 0.4, "deception": 0.2}

    def update_metric(self, name: str, value: float) -> None:
        """Update metric (backward-compatible)."""
        self.metrics[name] = value
        self._metric_history.setdefault(name, []).append(value)
        # Check alert thresholds
        if name in self._alert_thresholds and value > self._alert_thresholds[name]:
            self._alerts.append({"metric": name, "value": value, "threshold": self._alert_thresholds[name]})
        self._recalculate_safety_score()

    def add_incident(self, incident: dict[str, Any]) -> None:
        """Add incident (backward-compatible)."""
        self.incidents.append(incident)
        self._recalculate_safety_score()

    def _recalculate_safety_score(self) -> None:
        """Recalculate composite safety score."""
        incident_penalty = min(1.0, len(self.incidents) * 0.05)
        self.safety_score = round(max(0.0, min(1.0, 1.0 - incident_penalty)), 3)

    def get_dashboard(self) -> dict[str, Any]:
        """Get dashboard data (backward-compatible)."""
        return {
            "safety_score": round(self.safety_score, 3),
            "metrics": self.metrics,
            "recent_incidents": self.incidents[-5:],
            "status": "healthy" if self.safety_score > 0.8 else ("warning" if self.safety_score > 0.5 else "critical"),
            "active_alerts": len([a for a in self._alerts if a.get("value", 0) > a.get("threshold", 1)]),
        }

    def trend_report(self, metric: str, window: int = 10) -> dict[str, Any]:
        """Generate trend report for a metric."""
        history = self._metric_history.get(metric, [])
        if len(history) < 2:
            return {"metric": metric, "trend": "insufficient_data"}
        recent = history[-window:]
        trend = "improving" if recent[-1] > recent[0] else ("declining" if recent[-1] < recent[0] else "stable")
        return {"metric": metric, "trend": trend, "latest": recent[-1], "change": round(recent[-1] - recent[0], 3)}

    def add_alert_threshold(self, metric: str, threshold: float) -> None:
        """Add custom alert threshold."""
        self._alert_thresholds[metric] = threshold

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "metrics": len(self.metrics),
            "incidents": len(self.incidents),
            "alerts": len(self._alerts),
            "safety_score": round(self.safety_score, 3),
        }
