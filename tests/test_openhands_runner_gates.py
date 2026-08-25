from aios_core.openhands.gates import GateDecision, apply_gate, validate_gate
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole, Gate, TaskExtras


def test_orchestrator_gate_contract_requires_evidence_before_recording():
    extras = TaskExtras(task_id="gate-test")
    handoff = AgentHandoff(
        status="COMPLETED",
        summary="Tester completed",
        commands_run=("pytest tests/x.py",),
        evidence=("2 passed",),
        next_action="review",
        verdict="APPROVED",
    )
    result = apply_gate(AgentRole.TESTER, handoff, extras)
    assert result.decision is GateDecision.PASS
    assert Gate.TESTS in extras.passed_gates


def test_invalid_handoff_does_not_mutate_gate_state():
    extras = TaskExtras(task_id="gate-blocked")
    handoff = AgentHandoff(
        status="COMPLETED",
        summary="Tester completed",
        next_action="review",
        verdict="APPROVED",
    )
    result = validate_gate(AgentRole.TESTER, handoff)
    assert result.decision is GateDecision.BLOCK
    assert Gate.TESTS not in extras.passed_gates
