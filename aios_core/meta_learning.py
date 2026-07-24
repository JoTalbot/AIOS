"""Meta-Learning System for AIOS"""

from typing import Any, Dict, List


class MetaLearner:
    """Learns how to learn across different tasks."""

    def __init__(self):
        """Initialize MetaLearner."""
        self.task_history: List[Dict] = []
        self.strategies: dict[str, float] = {}

    def record_task(self, task_type: str, success: bool, duration: float) -> None:
        """Execute record task."""
        self.task_history.append({"type": task_type, "success": success, "duration": duration})

    def recommend_strategy(self, task_type: str) -> str:
        """Execute recommend strategy."""
        successes = [t for t in self.task_history if t["type"] == task_type and t["success"]]
        if len(successes) > 3:
            return "reuse_previous_approach"
        return "explore_new_approach"

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "tasks_learned": len(self.task_history),
            "strategies": len(self.strategies),
        }
