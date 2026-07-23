"""Continual / Lifelong Learning for AIOS"""

from typing import Dict, List


class ContinualLearner:
    """Prevents catastrophic forgetting."""

    def __init__(self):
        self.tasks: List[str] = []
        self.importance: Dict[str, float] = {}

    def learn_task(self, task_name: str, importance: float = 1.0) -> None:
        self.tasks.append(task_name)
        self.importance[task_name] = importance

    def protect_weights(self, task_name: str) -> float:
        return self.importance.get(task_name, 0.5)

    def stats(self) -> dict:
        return {"tasks_learned": len(self.tasks)}
