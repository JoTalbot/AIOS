from dataclasses import dataclass

@dataclass
class AuditRecord:
    action: str
    status: str

class EvolutionAudit:
    def __init__(self):
        self.records = []

    def record(self, action, status):
        self.records.append(AuditRecord(action, status))
