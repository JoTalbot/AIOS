"""Quality gates for staged OpenHands agent execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .handoff import AgentHandoff
from .models import AgentRole


class GateDecision(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class GateResult:
    role: AgentRole
    decision: GateDecision
    reasons: tuple[str, ...] = ()


def validate_gate(role: AgentRole, handoff: AgentHandoff) -> GateResult:
    """Fail closed when a stage has insufficient evidence or an invalid verdict."""
    reasons: list[str] = []
    if not handoff.status.strip():
        reasons.append("status missing")
    if not handoff.summary.strip():
        reasons.append("summary missing")
    if not handoff.evidence:
        reasons.append("evidence missing")
    if not handoff.next_action.strip():
        reasons.append("next_action missing")

    gate_roles = {AgentRole.TESTER, AgentRole.REVIEWER, AgentRole.SECURITY, AgentRole.QA}
    if role in gate_roles and handoff.verdict not in {"APPROVED", "CHANGES_REQUESTED"}:
        reasons.append("gate role requires APPROVED or CHANGES_REQUESTED")

    if role is AgentRole.CODER and not handoff.files_changed:
        reasons.append("coder handoff must list changed files")

    if role is AgentRole.ARCHITECT and not handoff.next_action:
        reasons.append("architect must provide next action")

    return GateResult(role, GateDecision.BLOCK if reasons else GateDecision.PASS, tuple(reasons))


def can_advance(result: GateResult) -> bool:
    return result.decision is GateDecision.PASS
