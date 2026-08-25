"""Small synchronous event bus for the AIOS runtime."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class AgentEvent:
    name: str
    task_id: str
    timestamp: str
    payload: dict[str, Any]


Subscriber = Callable[[AgentEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}
        self._history: list[AgentEvent] = []

    def subscribe(self, event_name: str, subscriber: Subscriber) -> None:
        self._subscribers.setdefault(event_name, []).append(subscriber)

    def publish(self, name: str, task_id: str, **payload: Any) -> AgentEvent:
        event = AgentEvent(
            name=name,
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )
        self._history.append(event)
        for subscriber in tuple(self._subscribers.get(name, ())):
            subscriber(event)
        for subscriber in tuple(self._subscribers.get("*", ())):
            subscriber(event)
        return event

    def history(self, task_id: str | None = None) -> tuple[AgentEvent, ...]:
        if task_id is None:
            return tuple(self._history)
        return tuple(event for event in self._history if event.task_id == task_id)
