from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole


def test_critical_checkpoint_carries_execution_identity():
    audit = OHAuditLogger()
    audit.log("gate_pass", "task-42", AgentRole.REVIEWER, decision="PASS", commit_sha="abc123")
    checkpoint = audit.chain.checkpoints[-1]
    assert checkpoint.task_id == "task-42"
    assert checkpoint.agent == AgentRole.REVIEWER.value
    assert checkpoint.gate_decision == "PASS"
    assert checkpoint.commit_sha == "abc123"
    assert audit.verify_chain()
