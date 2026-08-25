from aios_core.openhands.gates import GateDecision, apply_gate
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole, Gate, TaskExtras


def test_apply_gate_marks_required_gate_after_approval():
    extras = TaskExtras(task_id="t1", required_gates=frozenset({Gate.TESTS}))
    handoff = AgentHandoff(
        status="DONE",
        summary="tests completed",
        evidence=("pytest: 5 passed",),
        next_action="review",
        verdict="APPROVED",
    )
    result = apply_gate(AgentRole.TESTER, handoff, extras)
    assert result.decision is GateDecision.PASS
    assert Gate.TESTS in extras.passed_gates


def test_apply_gate_does_not_mark_gate_when_blocked():
    extras = TaskExtras(task_id="t2", required_gates=frozenset({Gate.TESTS}))
    handoff = AgentHandoff(status="DONE", summary="tests", next_action="review", verdict="APPROVED")
    result = apply_gate(AgentRole.TESTER, handoff, extras)
    assert result.decision is GateDecision.BLOCK
    assert Gate.TESTS not in extras.passed_gates
