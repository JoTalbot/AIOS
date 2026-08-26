from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class Event:
    type: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EventBus:
    def __init__(self):
        self.events: list[Event] = []
        self.handlers: dict[str, list] = {}

    def publish(self, event: Event):
        self.events.append(event)
        for handler in self.handlers.get(event.type, []):
            handler(event)

    def subscribe(self, event_type: str, handler):
        self.handlers.setdefault(event_type, []).append(handler)
