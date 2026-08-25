import pytest

from aios_core.openhands.audit_chain import AuditChain


def test_checkpoints_form_a_hash_chain():
    chain = AuditChain()
    chain.append("e1", {"type": "openhands.start"})
    first = chain.checkpoint(task_id="task-1", agent="coder", commit_sha="a" * 40, diff_hash="b" * 64)
    chain.append("e2", {"type": "openhands.gate_pass", "decision": "APPROVED"})
    second = chain.checkpoint(task_id="task-1", agent="reviewer", gate_decision="APPROVED", commit_sha="c" * 40, diff_hash="d" * 64)
    assert second.previous_checkpoint_hash == first.checkpoint_hash
    assert chain.verify()


def test_checkpoint_deletion_is_detected():
    chain = AuditChain()
    chain.append("e1", {"type": "openhands.start"})
    first = chain.checkpoint(task_id="task-1")
    chain.append("e2", {"type": "openhands.gate_pass"})
    second = chain.checkpoint(task_id="task-1", gate_decision="APPROVED")
    stored = [
        {"type": "openhands.start", "event_id": "e1", "parent_event_id": None, "event_hash": chain.events[0].event_hash, "timestamp": "1"},
        {"type": "openhands.gate_pass", "event_id": "e2", "parent_event_id": "e1", "event_hash": chain.events[1].event_hash, "timestamp": "2"},
        {"type": "openhands.audit_checkpoint", "sequence": second.sequence, "last_event_id": second.last_event_id, "root_hash": second.root_hash, "task_id": second.task_id, "agent": second.agent, "gate_decision": second.gate_decision, "commit_sha": second.commit_sha, "diff_hash": second.diff_hash, "previous_checkpoint_hash": "not-the-first-checkpoint", "checkpoint_hash": second.checkpoint_hash},
    ]
    with pytest.raises(ValueError):
        AuditChain.from_persisted(stored)
