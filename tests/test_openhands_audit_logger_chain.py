from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole


def test_audit_logger_emits_linked_hash_events():
    audit = OHAuditLogger()
    first = audit.log("start", "task-1", AgentRole.CODER, note="hello")
    second = audit.log("decision", "task-1", AgentRole.CODER, decision="PASS")
    assert first["event_id"]
    assert second["parent_event_id"] == first["event_id"]
    assert second["event_hash"]
    assert audit.verify_chain()


def test_audit_logger_masks_secret_before_hashing_and_persistence():
    audit = OHAuditLogger()
    event = audit.log("start", "task-1", AgentRole.CODER, api_key="super-secret-token-value-123456")
    assert event["api_key"] == "***"
    assert "super-secret-token-value-123456" not in str(event)
    assert audit.verify_chain()
