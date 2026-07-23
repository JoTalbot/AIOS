"""Edge Computing Support for AIOS"""

from typing import Dict, List


class EdgeNode:
    """Represents an edge computing node."""

    def __init__(self, node_id: str, location: str, capacity: int = 100):
        self.node_id = node_id
        self.location = location
        self.capacity = capacity
        self.load = 0

    def can_handle(self, task_size: int) -> bool:
        """Execute can handle."""
        return self.load + task_size <= self.capacity

    def assign(self, task_size: int) -> None:
        """Execute assign."""
        self.load += task_size

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "id": self.node_id,
            "location": self.location,
            "load": self.load,
            "capacity": self.capacity,
        }


class EdgeOrchestrator:
    """Orchestrates tasks across edge nodes."""

    def __init__(self):
        self.nodes: Dict[str, EdgeNode] = {}

    def register_node(self, node: EdgeNode) -> None:
        """Execute register node."""
        self.nodes[node.node_id] = node

    def schedule(self, task_size: int, preferred_location: str = None) -> str:
        """Execute schedule."""
        for node in sorted(self.nodes.values(), key=lambda n: n.load):
            if node.can_handle(task_size):
                node.assign(task_size)
                return node.node_id
        return None

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"nodes": len(self.nodes)}
