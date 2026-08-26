"""Structured, append-only lifecycle audit trail for vNext execution."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent


@dataclass(frozen=True)
class AuditEvent:
    event: str
    agent_id: str
    tool: Optional[str] = None
    status: str = "ok"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_id: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    attempt: Optional[int] = None
    reason: Optional[str] = None


class ExecutionAudit:
    def __init__(self, path: Optional[str] = None):
        self.events: List[AuditEvent] = []
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, agent_id: str, tool: Optional[str] = None, status: str = "ok", context: Optional[ExecutionContext] = None, **metadata):
        item = AuditEvent(event, agent_id, tool, status, metadata, execution_id=getattr(context, "execution_id", None))
        self.events.append(item)
        self._persist(item)
        return item

    def record_transition(self, execution_id: str, agent_id: str, from_status: str, to_status: str, attempt: int = 0, reason: Optional[str] = None):
        item = AuditEvent("execution.transition", agent_id, status="ok", execution_id=execution_id,
                          from_status=from_status, to_status=to_status, attempt=attempt, reason=reason)
        self.events.append(item)
        self._persist(item)
        return item

    def record_event(self, event: ExecutionEvent):
        return self.record(event.type, event.context.agent_id, context=event.context, **event.data)

    def _persist(self, item: AuditEvent):
        if self.path:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(item), ensure_ascii=False, default=str) + "\n")

    def snapshot(self):
        return list(self.events)

    def load(self, execution_id: Optional[str] = None):
        if not self.path or not self.path.exists():
            return []
        result = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = AuditEvent(**json.loads(line))
                if execution_id is None or item.execution_id == execution_id:
                    result.append(item)
        return result
