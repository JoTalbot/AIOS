"""Structured audit trail for vNext tool execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AuditEvent:
    event: str
    agent_id: str
    tool: Optional[str] = None
    status: str = "ok"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionAudit:
    def __init__(self):
        self.events: List[AuditEvent] = []

    def record(self, event: str, agent_id: str, tool: Optional[str] = None, status: str = "ok", **metadata):
        item = AuditEvent(event, agent_id, tool, status, metadata)
        self.events.append(item)
        return item

    def snapshot(self):
        return list(self.events)
