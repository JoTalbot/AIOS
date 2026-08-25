from aios_core.openhands.audit_chain import AuditChain


def test_persisted_checkpoint_is_restored_and_verified():
    chain = AuditChain()
    event = chain.append("e1", {"type": "openhands.gate_pass", "task_id": "t1", "agent": "reviewer", "decision": "PASS"})
    checkpoint = chain.checkpoint(task_id="t1", agent="reviewer", gate_decision="PASS", commit_sha="abc123", diff_hash="d" * 64)
    stored = [
        {"type": "openhands.gate_pass", "event_id": event.event_id, "parent_event_id": None, "task_id": "t1", "agent": "reviewer", "decision": "PASS", "event_hash": event.event_hash, "timestamp": "1"},
        {"type": "openhands.audit_checkpoint", "task_id": "t1", "agent": "reviewer", "sequence": checkpoint.sequence, "last_event_id": checkpoint.last_event_id, "root_hash": checkpoint.root_hash, "gate_decision": "PASS", "commit_sha": "abc123", "diff_hash": "d" * 64, "timestamp": "2"},
    ]
    restored = AuditChain.from_persisted(stored)
    assert restored.verify()
    assert restored.checkpoints[-1] == checkpoint


def test_tampered_checkpoint_root_is_rejected():
    chain = AuditChain()
    event = chain.append("e1", {"type": "openhands.gate_pass"})
    checkpoint = chain.checkpoint(task_id="t1", agent="reviewer", gate_decision="PASS", commit_sha="abc123", diff_hash="d" * 64)
    stored = [
        {"type": "openhands.gate_pass", "event_id": event.event_id, "parent_event_id": None, "event_hash": event.event_hash, "timestamp": "1"},
        {"type": "openhands.audit_checkpoint", "task_id": "t1", "agent": "reviewer", "sequence": checkpoint.sequence, "last_event_id": checkpoint.last_event_id, "root_hash": "tampered", "gate_decision": "PASS", "commit_sha": "abc123", "diff_hash": "d" * 64, "timestamp": "2"},
    ]
    try:
        AuditChain.from_persisted(stored)
    except ValueError:
        return
    raise AssertionError("tampered checkpoint must be rejected")
