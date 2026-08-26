"""Distributed agent mesh coordination primitives."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass
class MeshEvent:
    name: str
    source: str
    target: str = "broadcast"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    delivery_status: str = "pending"


class AgentMesh:
    """Lightweight coordination bus for multiple AIOS agents."""

    def __init__(self):
        self._events: List[MeshEvent] = []
        self._subscribers: List[Callable[[MeshEvent], None]] = []
        self._delivery_callbacks: List[Callable[[MeshEvent], None]] = []

    def publish(self, name: str, source: str, target: str = "broadcast", **payload):
        event = MeshEvent(name=name, source=source, target=target, payload=payload)
        self._events.append(event)
        self._deliver(event)
        return event

    def subscribe(self, callback: Callable[[MeshEvent], None]):
        self._subscribers.append(callback)
        return callback

    def unsubscribe(self, callback: Callable[[MeshEvent], None]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def register_delivery_callback(self, callback: Callable[[MeshEvent], None]):
        self._delivery_callbacks.append(callback)
        return callback

    def unregister_delivery_callback(self, callback: Callable[[MeshEvent], None]):
        if callback in self._delivery_callbacks:
            self._delivery_callbacks.remove(callback)

    def _deliver(self, event: MeshEvent):
        for callback in list(self._subscribers):
            callback(event)
        event.delivery_status = "delivered"
        for callback in list(self._delivery_callbacks):
            callback(event)

    def acknowledge(self, event: MeshEvent):
        event.acknowledged = True
        event.delivery_status = "acknowledged"
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
            "subscribers": len(self._subscribers),
            "delivery_callbacks": len(self._delivery_callbacks),
            "acknowledged": sum(event.acknowledged for event in self._events),
        }
