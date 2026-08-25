from unittest.mock import Mock

import pytest

from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole
from aios_core.openhands.runner import OHOrchestrator
from aios_core.openhands.state_machine import TransitionError


def test_gate_audit_uses_real_git_identity():
    github = Mock()
    github.head_sha.return_value = "abc123"
    github.diff_hash.return_value = "d" * 64
    audit = OHAuditLogger()
    runner = OHOrchestrator(client=Mock(), github=github, audit=audit, base_branch="main")
    runner._audit_gate_identity("task-1", AgentRole.REVIEWER, "gate_pass", decision="APPROVED", branch="agent/oh-task-1")
    checkpoint = audit.chain.checkpoints[-1]
    assert checkpoint.commit_sha == "abc123"
    assert checkpoint.diff_hash == "d" * 64
    assert checkpoint.gate_decision == "APPROVED"
    github.head_sha.assert_called_once_with("agent/oh-task-1")
    github.diff_hash.assert_called_once_with("main", "agent/oh-task-1")


def test_gate_audit_fails_closed_when_git_identity_unavailable():
    github = Mock()
    github.head_sha.side_effect = RuntimeError("git unavailable")
    runner = OHOrchestrator(client=Mock(), github=github, audit=OHAuditLogger(), base_branch="main")
    with pytest.raises(TransitionError, match="Git identity"):
        runner._audit_gate_identity("task-1", AgentRole.REVIEWER, "gate_pass", decision="APPROVED", branch="agent/oh-task-1")
