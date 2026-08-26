"""Distributed execution context primitives for AIOS federation."""

from dataclasses import dataclass, field
import uuid


@dataclass
class DistributedContext:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict = field(default_factory=dict)

    def propagate(self):
        return {
            "node_id": self.node_id,
            "metadata": self.metadata,
        }
