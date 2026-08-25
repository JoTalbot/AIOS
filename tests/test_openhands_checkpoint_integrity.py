import pytest

from aios_core.openhands.audit_chain import AuditChain


def test_checkpoint_metadata_is_cryptographically_bound():
    chain = AuditChain()
    event = chain.append("e1", {"action": "gate_pass"})
    checkpoint = chain.checkpoint(task_id="task-1", agent="reviewer", gate_decision="PASS", commit_sha="abc", diff_hash="def")
    assert len(checkpoint.checkpoint_hash) == 64
    assert chain.verify()

    tampered = type(checkpoint)(
        checkpoint.sequence,
        checkpoint.last_event_id,
        checkpoint.root_hash,
        checkpoint.task_id,
        checkpoint.agent,
        "BLOCK",
        checkpoint.commit_sha,
        checkpoint.diff_hash,
        checkpoint.checkpoint_hash,
    )
    chain._checkpoints[-1] = tampered
    assert not chain.verify()


def test_persisted_checkpoint_requires_integrity_hash():
    chain = AuditChain()
    event = chain.append("e1", {"action": "gate_pass"})
    checkpoint = chain.checkpoint(task_id="task-1", agent="reviewer", gate_decision="PASS", commit_sha="abc", diff_hash="def")
    stored = [
        {"type": "openhands.gate_pass", "event_id": event.event_id, "parent_event_id": None, "action": "gate_pass", "event_hash": event.event_hash, "timestamp": "1"},
        {"type": "openhands.audit_checkpoint", "sequence": checkpoint.sequence, "last_event_id": checkpoint.last_event_id, "root_hash": checkpoint.root_hash, "task_id": checkpoint.task_id, "agent": checkpoint.agent, "gate_decision": checkpoint.gate_decision, "commit_sha": checkpoint.commit_sha, "diff_hash": checkpoint.diff_hash, "timestamp": "2"},
    ]
    with pytest.raises(ValueError, match="checkpoint"):
        AuditChain.from_persisted(stored)
