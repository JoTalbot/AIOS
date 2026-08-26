"""Audit trail for Digital Twin decisions and simulations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AuditEntry:
    event: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TwinAuditLog:
    def __init__(self):
        self.entries: List[AuditEntry] = []

    def record(self, event: str, data: Dict[str, Any]) -> AuditEntry:
        entry = AuditEntry(event, data)
        self.entries.append(entry)
        return entry
