from aios_core.runtime.audit import AuditLog
from aios_core.runtime.events import EventBus


def test_audit_log_receives_runtime_events():
    bus = EventBus()
    audit = AuditLog()
    audit.attach(bus)

    bus.publish("AGENT_STARTED", "task-1", status="running")
    bus.publish("AGENT_COMPLETED", "task-1", status="completed")

    records = audit.records("task-1")
    assert len(records) == 2
    assert records[0].event.name == "AGENT_STARTED"
    assert records[1].event.payload["status"] == "completed"
