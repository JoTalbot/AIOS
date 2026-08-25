from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole


class MemoryAuditBackend:
    def __init__(self):
        self.events = []

    def record(self, event):
        event = dict(event)
        event.setdefault("timestamp", str(len(self.events)))
        event.setdefault("id", str(len(self.events)))
        self.events.append(event)
        return event

    def query(self, **kwargs):
        return list(self.events)


def test_chain_survives_logger_reconstruction():
    backend = MemoryAuditBackend()
    first = OHAuditLogger(logger=backend)
    first.log("start", "task-1", AgentRole.CODER)
    first.log("decision", "task-1", AgentRole.CODER, decision="PASS")

    restored = OHAuditLogger(logger=backend)
    assert restored.verify_chain()
    assert len(restored.chain.events) == 2
    event = restored.log("finish", "task-1", AgentRole.CODER)
    assert event["parent_event_id"] == restored.chain.events[-2].event_id
    assert restored.verify_chain()
