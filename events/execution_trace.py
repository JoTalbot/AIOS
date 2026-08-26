"""Execution trace model foundation."""

from dataclasses import dataclass, field
from time import time

@dataclass
class ExecutionTrace:
    trace_id: str
    events: list = field(default_factory=list)
    created_at: float = field(default_factory=time)

    def add(self, event):
        self.events.append(event)
