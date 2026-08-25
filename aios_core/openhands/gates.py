"""Quality gates for staged OpenHands agent execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .evidence import CompletionReport, dod_for_role
from .file_evidence import FileEvidence, verify_handoff_files
from .handoff import AgentHandoff
from .models import AgentRole, Gate, TaskExtras


class GateDecision(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"


_ROLE_GATE: dict[AgentRole, Gate] = {
    AgentRole.TESTER: Gate.TESTS,
    AgentRole.REVIEWER: Gate.REVIEW,
    AgentRole.SECURITY: Gate.SECURITY_REVIEW,
    AgentRole.QA: Gate.QA,
}


@dataclass(frozen=True)
class GateResult:
    role: AgentRole
    decision: GateDecision
    reasons: tuple[str, ...] = ()
    file_evidence: FileEvidence | None = None


def validate_gate(role: AgentRole, handoff: AgentHandoff, report: CompletionReport | None = None, *, actual_files: Iterable[str] | None = None) -> GateResult:
    """Fail closed unless handoff, verified report and supplied git reality pass."""
    reasons: list[str] = []
    file_evidence = None
    if not handoff.status.strip(): reasons.append("status missing")
    if not handoff.summary.strip(): reasons.append("summary missing")
    if not handoff.evidence: reasons.append("handoff evidence missing")
    if not handoff.next_action.strip(): reasons.append("next_action missing")
    if report is not None:
        required = dod_for_role(role.value)
        if not report.required_dod_passed(required): reasons.append("required DoD not satisfied")
        if not report.evidence_passed(): reasons.append("verified evidence missing or failed")
    if actual_files is not None:
        file_evidence = verify_handoff_files(role, handoff, actual_files)
        if not file_evidence.passed:
            reasons.append("git file evidence does not match handoff or permissions")
    if role in _ROLE_GATE and handoff.verdict not in {"APPROVED", "CHANGES_REQUESTED"}:
        reasons.append("gate role requires APPROVED or CHANGES_REQUESTED")
    if role is AgentRole.CODER and not handoff.files_changed:
        reasons.append("coder handoff must list changed files")
    return GateResult(role, GateDecision.BLOCK if reasons else GateDecision.PASS, tuple(reasons), file_evidence)


def can_advance(result: GateResult) -> bool:
    return result.decision is GateDecision.PASS


def apply_gate(role: AgentRole, handoff: AgentHandoff, extras: TaskExtras, report: CompletionReport | None = None, *, actual_files: Iterable[str] | None = None) -> GateResult:
    """Validate handoff, verified report and optional git reality before recording a gate."""
    result = validate_gate(role, handoff, report, actual_files=actual_files)
    if not can_advance(result):
        return result
    gate = _ROLE_GATE.get(role)
    if gate is not None:
        extras.mark_gate_passed(gate)
    return result
