from aios_core.openhands.gates import GateDecision, apply_gate
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole, TaskExtras


def test_gate_blocks_when_git_files_differ_from_handoff():
    handoff = AgentHandoff(
        status="DONE",
        summary="reviewed",
        files_changed=("src/a.py",),
        evidence=("diff checked",),
        next_action="handoff",
        verdict="APPROVED",
    )
    extras = TaskExtras()
    result = apply_gate(
        AgentRole.REVIEWER,
        handoff,
        extras,
        actual_files=("src/a.py", "src/hidden.py"),
    )
    assert result.decision is GateDecision.BLOCK
    assert not extras.passed_gates
    assert result.file_evidence is not None
    assert result.file_evidence.missing_from_handoff == ("src/hidden.py",)


def test_gate_passes_when_git_files_match_handoff():
    handoff = AgentHandoff(
        status="DONE",
        summary="reviewed",
        files_changed=("src/a.py",),
        evidence=("diff checked",),
        next_action="handoff",
        verdict="APPROVED",
    )
    extras = TaskExtras()
    result = apply_gate(
        AgentRole.REVIEWER,
        handoff,
        extras,
        actual_files=("src/a.py",),
    )
    assert result.decision is GateDecision.PASS
