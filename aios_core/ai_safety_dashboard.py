"""AI Safety Dashboard for AIOS"""

from typing import Dict, List

__all__ = ["SafetyDashboard"]


class SafetyDashboard:
    """Real-time safety monitoring dashboard."""

    def __init__(self):
        self.metrics: Dict[str, float] = {}
        self.incidents: List[Dict] = []
        self.safety_score = 1.0

    def update_metric(self, name: str, value: float):
        self.metrics[name] = value
        self._recalculate_safety_score()

    def add_incident(self, incident: Dict):
        self.incidents.append(incident)
        self._recalculate_safety_score()

    def _recalculate_safety_score(self):
        if not self.incidents:
            self.safety_score = 1.0
        else:
            self.safety_score = max(0.0, 1.0 - len(self.incidents) * 0.05)

    def get_dashboard(self) -> Dict:
        return {
            "safety_score": round(self.safety_score, 3),
            "metrics": self.metrics,
            "recent_incidents": self.incidents[-5:],
            "status": "healthy" if self.safety_score > 0.8 else "warning",
        }

    def stats(self) -> dict:
        return {"metrics": len(self.metrics), "incidents": len(self.incidents)}
