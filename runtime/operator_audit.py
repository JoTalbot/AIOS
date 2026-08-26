"""Durable, typed audit trail for operator recovery actions."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Optional


class OperatorAuditAction(str, Enum):
    RESOLVE = "resolve"
    RETRY = "retry"
    QUARANTINE = "quarantine"
    MANUAL_REVIEW = "manual_review"


class OperatorAuditOutcome(str, Enum):
    RESOLVED = "resolved"
    FAILED = "failed"


@dataclass(frozen=True)
class OperatorAuditEvent:
    action: str
    execution_id: str
    actor: str
    outcome: str
    reason: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OperatorAuditLog:
    def __init__(self, path: str = "data/operator_audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: OperatorAuditEvent):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event

    def events(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
