"""Execution audit events.

Keeps execution lifecycle observable without coupling runtime implementations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExecutionAuditEvent:
    event: str
    context: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionAudit:
    """In-memory execution audit collector.

    Can later be replaced by persistent telemetry/event storage.
    """

    def __init__(self):
        self.events: list[ExecutionAuditEvent] = []

    def emit(self, event: str, context: Any = None, **metadata: Any) -> ExecutionAuditEvent:
        record = ExecutionAuditEvent(
            event=event,
            context=context,
            metadata=metadata,
        )
        self.events.append(record)
        return record
