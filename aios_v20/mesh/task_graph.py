"""AIOS v20 Task Graph Engine.

Coordinates dependent tasks across agents through governed execution.
"""

from dataclasses import dataclass, field


@dataclass
class TaskNode:
    id: str
    agent: str
    capability: str
    dependencies: list[str] = field(default_factory=list)


class TaskGraph:
    def __init__(self):
        self.nodes = {}

    def add_task(self, task: TaskNode):
        self.nodes[task.id] = task

    def get_ready_tasks(self):
        return [
            task for task in self.nodes.values()
            if all(dep not in self.nodes for dep in task.dependencies)
        ]
