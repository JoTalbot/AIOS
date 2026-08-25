import pytest

from aios_core.openhands.audit_chain import AuditChain


def _event(event_id, parent, payload, event_hash, timestamp):
    return {
        "type": "openhands.start",
        "event_id": event_id,
        "parent_event_id": parent,
        "payload": payload,
        "event_hash": event_hash,
        "timestamp": timestamp,
    }


def test_restore_rejects_tampered_chain():
    chain = AuditChain()
    first = chain.append("e1", {"action": "start"})
    stored = [
        _event("e1", None, {"type": "openhands.start", "payload": {"action": "start"}}, "bad", "1"),
    ]
    with pytest.raises(ValueError, match="audit chain"):
        AuditChain.from_persisted(stored)


def test_restore_rejects_checkpoint_after_truncation():
    chain = AuditChain()
    first = chain.append("e1", {"action": "start"})
    checkpoint = chain.checkpoint()
    stored = [
        {"type": "openhands.start", "event_id": "e1", "parent_event_id": None, "action": "start", "event_hash": first.event_hash, "timestamp": "1"},
        {"type": "openhands.audit_checkpoint", "event_id": "cp", "sequence": checkpoint.sequence, "last_event_id": checkpoint.last_event_id, "root_hash": checkpoint.root_hash, "timestamp": "2"},
    ]
    assert AuditChain.from_persisted(stored).verify()
    with pytest.raises(ValueError):
        AuditChain.from_persisted([stored[1]])
