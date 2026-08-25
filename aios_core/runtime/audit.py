"""Audit subscriber for AIOS runtime events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .events import AgentEvent, EventBus


@dataclass(frozen=True)
class AuditRecord:
    event: AgentEvent


class AuditLog:
    """In-memory append-only audit sink; persistence can be layered later."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record(self, event: AgentEvent) -> None:
        self._records.append(AuditRecord(event))

    def records(self, task_id: str | None = None) -> tuple[AuditRecord, ...]:
        if task_id is None:
            return tuple(self._records)
        return tuple(record for record in self._records if record.event.task_id == task_id)

    def attach(self, bus: EventBus, event_name: str = "*") -> None:
        bus.subscribe(event_name, self.record)
