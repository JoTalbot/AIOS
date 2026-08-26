"""AIOS Runtime Event Bus."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RuntimeEvent:
    name: str
    payload: dict
    created_at: str = datetime.utcnow().isoformat()


class EventBus:
    def __init__(self):
        self.events = []

    def publish(self, event: RuntimeEvent):
        self.events.append(event)

    def history(self):
        return self.events
