from aios_core.openhands.evidence import CompletionReport, Evidence, EvidenceKind
from aios_core.openhands.gates import GateDecision, apply_gate
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole, TaskExtras


def _handoff():
    return AgentHandoff(status="DONE", summary="verified", evidence=("pytest passed",), next_action="handoff", verdict="APPROVED")


def test_gate_blocks_when_verified_evidence_is_missing():
    extras = TaskExtras()
    report = CompletionReport()
    result = apply_gate(AgentRole.REVIEWER, _handoff(), extras, report)
    assert result.decision is GateDecision.BLOCK
    assert not extras.passed_gates


def test_gate_passes_with_required_dod_and_passing_evidence():
    extras = TaskExtras()
    report = CompletionReport(
        evidence=[Evidence(EvidenceKind.REVIEW, "git diff --check", "clean", True)],
        dod={"requirements": True, "architecture": True, "tests": True, "security": True, "evidence": True},
    )
    result = apply_gate(AgentRole.REVIEWER, _handoff(), extras, report)
    assert result.decision is GateDecision.PASS
