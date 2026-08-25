from aios_core.openhands.gates import GateDecision, can_advance, validate_gate
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole


def test_reviewer_cannot_advance_without_valid_verdict():
    handoff = AgentHandoff(status="DONE", summary="review", evidence=("diff checked",), next_action="fix")
    result = validate_gate(AgentRole.REVIEWER, handoff)
    assert result.decision is GateDecision.BLOCK
    assert not can_advance(result)


def test_reviewer_can_advance_with_evidence_and_approved_verdict():
    handoff = AgentHandoff(status="DONE", summary="review passed", evidence=("pytest: 5 passed",), next_action="handoff", verdict="APPROVED")
    result = validate_gate(AgentRole.REVIEWER, handoff)
    assert result.decision is GateDecision.PASS
    assert can_advance(result)


def test_coder_requires_changed_files():
    handoff = AgentHandoff(status="DONE", summary="implemented", evidence=("tests passed",), next_action="review")
    result = validate_gate(AgentRole.CODER, handoff)
    assert result.decision is GateDecision.BLOCK
