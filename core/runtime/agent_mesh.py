"""Distributed agent mesh coordination primitives."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class MeshEvent:
    name: str
    source: str
    target: str = "broadcast"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMesh:
    """Lightweight coordination bus for multiple AIOS agents."""

    def __init__(self):
        self._events: List[MeshEvent] = []

    def publish(self, name: str, source: str, target: str = "broadcast", **payload):
        event = MeshEvent(name=name, source=source, target=target, payload=payload)
        self._events.append(event)
        return event

    def events(self, target: str = None):
        if target is None:
            return list(self._events)
        return [event for event in self._events if event.target in (target, "broadcast")]

    def clear(self):
        self._events.clear()

    def snapshot(self):
        return {
            "events": len(self._events),
            "agents": sorted({event.source for event in self._events}),
        }
