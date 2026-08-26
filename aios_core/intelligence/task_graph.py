"""AIOS Task Graph Engine foundation."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TaskNode:
    task_id: str
    dependencies: List[str] = field(default_factory=list)


class TaskGraph:
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}

    def add_task(self, task_id: str, dependencies=None):
        self.nodes[task_id] = TaskNode(task_id, dependencies or [])

    def get_dependencies(self, task_id: str):
        node = self.nodes.get(task_id)
        return node.dependencies if node else []
