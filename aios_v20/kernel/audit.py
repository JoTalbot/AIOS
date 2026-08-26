from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class AuditEvent:
    action: str
    actor: str
    result: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AuditLedger:
    def __init__(self):
        self.records: list[AuditEvent] = []

    def record(self, event: AuditEvent):
        self.records.append(event)

    def history(self):
        return self.records
