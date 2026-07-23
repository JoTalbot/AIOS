"""Experiment Tracking for AIOS"""

from typing import Dict, Any, List
import uuid


class ExperimentTracker:
    """Track ML experiments and results."""

    def __init__(self):
        self.experiments: Dict[str, Dict] = {}

    def start_experiment(self, name: str, params: Dict) -> str:
        exp_id = str(uuid.uuid4())[:8]
        self.experiments[exp_id] = {
            "name": name,
            "params": params,
            "metrics": {},
            "status": "running",
        }
        return exp_id

    def log_metric(self, exp_id: str, metric: str, value: float):
        if exp_id in self.experiments:
            self.experiments[exp_id]["metrics"][metric] = value

    def end_experiment(self, exp_id: str, status: str = "completed"):
        if exp_id in self.experiments:
            self.experiments[exp_id]["status"] = status

    def stats(self) -> dict:
        return {"experiments": len(self.experiments)}
