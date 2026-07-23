"""Integration: Event Bus + Audit Logger cross-module."""
from aios_core.event_bus import EventBus
from aios_core.audit_logger import AuditLogger
def test_event_audit_integration():
    eb = EventBus()
    al = AuditLogger()
    events = []
    eb.on("audit_event", lambda p: events.append(p))
    eb.emit("audit_event", {"action": "test", "user": "admin"})
    assert len(events) == 1
    assert events[0]["action"] == "test"
