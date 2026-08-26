"""AIOS execution graph foundation."""

from dataclasses import dataclass, field


@dataclass
class ExecutionNode:
    name: str
    dependencies: list[str] = field(default_factory=list)


class ExecutionGraph:
    def __init__(self):
        self.nodes = []

    def add(self, node: ExecutionNode):
        self.nodes.append(node)
