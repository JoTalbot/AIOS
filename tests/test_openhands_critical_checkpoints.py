from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole


def test_critical_actions_create_checkpoints():
    audit = OHAuditLogger()
    audit.log("start", "task-1", AgentRole.CODER)
    audit.log("handoff", "task-1", AgentRole.CODER)
    audit.log("gate_pass", "task-1", AgentRole.REVIEWER)
    audit.log("security_review", "task-1", AgentRole.SECURITY)
    assert len(audit.chain.checkpoints) == 3
    assert audit.verify_chain()


def test_noncritical_action_does_not_create_checkpoint():
    audit = OHAuditLogger()
    audit.log("command", "task-1", AgentRole.CODER, command="pytest")
    assert not audit.chain.checkpoints
