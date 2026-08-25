from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole


def test_checkpoint_carries_commit_and_diff_hash():
    audit = OHAuditLogger()
    audit.log("gate_pass", "task-42", AgentRole.REVIEWER, decision="PASS", commit_sha="abc123", diff_hash="deadbeef")
    checkpoint = audit.chain.checkpoints[-1]
    assert checkpoint.commit_sha == "abc123"
    assert checkpoint.diff_hash == "deadbeef"
    assert audit.verify_chain()
