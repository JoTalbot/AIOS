from unittest.mock import Mock

import pytest

from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import Gate, TaskExtras
from aios_core.openhands.runner import OHOrchestrator
from aios_core.openhands.state_machine import TransitionError


def test_runner_finalize_blocks_without_evidence():
    github = Mock()
    github.head_sha.return_value = "a" * 40
    github.diff_hash.return_value = "b" * 64
    github.changed_files.return_value = ["src/example.py"]
    audit = OHAuditLogger()
    runner = OHOrchestrator(client=Mock(), github=github, audit=audit, base_branch="main")
    extras = TaskExtras(task_id="task-1", required_gates=frozenset({Gate.TESTS, Gate.REVIEW}))
    extras.passed_gates = frozenset({Gate.TESTS, Gate.REVIEW})
    with pytest.raises(TransitionError, match="missing evidence"):
        runner._finalize("task-1", "title", "description", extras, "agent/oh-task-1")
