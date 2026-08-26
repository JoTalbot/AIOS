"""Structured audit trail for vNext tool execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent


@dataclass
class AuditEvent:
    event: str
    agent_id: str
    tool: Optional[str] = None
    status: str = "ok"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_id: Optional[str] = None


class ExecutionAudit:
    def __init__(self):
        self.events: List[AuditEvent] = []

    def record(self, event: str, agent_id: str, tool: Optional[str] = None, status: str = "ok", context: Optional[ExecutionContext] = None, **metadata):
        item = AuditEvent(event, agent_id, tool, status, metadata, execution_id=getattr(context, "execution_id", None))
        self.events.append(item)
        return item

    def record_event(self, event: ExecutionEvent):
        return self.record(event.type, event.context.agent_id, context=event.context, **event.data)

    def snapshot(self):
        return list(self.events)
