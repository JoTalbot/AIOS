"""Event-backed task memory subscriber for the AIOS runtime."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .events import AgentEvent, EventBus


@dataclass(frozen=True)
class MemoryEntry:
    task_id: str
    event_name: str
    timestamp: str
    payload: dict[str, Any]


class TaskMemory:
    """Small append-only task memory fed by runtime events."""

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    def remember(self, event: AgentEvent) -> None:
        self._entries.append(
            MemoryEntry(
                task_id=event.task_id,
                event_name=event.name,
                timestamp=event.timestamp,
                payload=dict(event.payload),
            )
        )

    def attach(self, bus: EventBus, event_name: str = "*") -> None:
        bus.subscribe(event_name, self.remember)

    def entries(self, task_id: str | None = None) -> tuple[MemoryEntry, ...]:
        if task_id is None:
            return tuple(self._entries)
        return tuple(entry for entry in self._entries if entry.task_id == task_id)

    def context(self, task_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "event": entry.event_name,
                "timestamp": entry.timestamp,
                **entry.payload,
            }
            for entry in self.entries(task_id)
        )
