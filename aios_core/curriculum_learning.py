"""Curriculum Learning for AIOS"""

from typing import List, Dict, Any


class Curriculum:
    """Progressive difficulty curriculum."""

    def __init__(self):
        self.stages: List[Dict] = []
        self.current_stage = 0

    def add_stage(self, name: str, difficulty: float, tasks: List):
        self.stages.append({"name": name, "difficulty": difficulty, "tasks": tasks, "completed": 0})

    def next_task(self) -> Any:
        if not self.stages:
            return None
        stage = self.stages[min(self.current_stage, len(self.stages) - 1)]
        if stage["tasks"]:
            return stage["tasks"][0]
        return None

    def complete_task(self):
        if self.stages and self.current_stage < len(self.stages):
            self.stages[self.current_stage]["completed"] += 1
            if self.stages[self.current_stage]["completed"] >= 5:
                self.current_stage += 1

    def stats(self) -> dict:
        return {"stages": len(self.stages), "current_stage": self.current_stage}
