import pytest

from aios_core.openhands.handoff import AgentHandoff


def test_handoff_serializes_evidence_and_next_action():
    handoff = AgentHandoff(
        status="COMPLETED",
        summary="Implemented runtime guard",
        files_changed=("aios_core/runtime/x.py",),
        commands_run=("pytest tests/test_x.py",),
        evidence=("1 passed",),
        risks=("Docker not available",),
        next_action="Run Docker E2E in CI",
    )
    text = handoff.to_prompt()
    assert "COMMANDS_RUN: pytest tests/test_x.py" in text
    assert "EVIDENCE: 1 passed" in text
    assert "NEXT_ACTION: Run Docker E2E in CI" in text


def test_gate_handoff_requires_valid_verdict():
    handoff = AgentHandoff(status="DONE", summary="Review complete", verdict=None)
    with pytest.raises(ValueError):
        handoff.validate(gate_role=True)


def test_gate_handoff_accepts_only_approved_or_changes_requested():
    handoff = AgentHandoff(status="DONE", summary="Review complete", verdict="MAYBE")
    with pytest.raises(ValueError):
        handoff.validate(gate_role=True)
