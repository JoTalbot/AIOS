"""Fail-closed completion gate for OpenHands evidence."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .models import Gate, ReviewDecision, TaskExtras


class EvidenceGateStatus(StrEnum):
    PASS = "pass"
    BLOCK = "block"


@dataclass(frozen=True)
class EvidenceGateResult:
    status: EvidenceGateStatus
    missing: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.status == EvidenceGateStatus.PASS


class EvidenceGate:
    """Single authoritative, fail-closed gate for transition to COMPLETED."""

    REQUIRED = ("task_id", "commit_sha", "diff_hash", "changed_files", "tests", "reviewer", "security", "audit_checkpoint", "audit_chain")

    def evaluate(self, extras: TaskExtras, evidence: Mapping[str, Any] | None = None) -> EvidenceGateResult:
        evidence = evidence or {}
        missing: list[str] = []
        if not extras.task_id:
            missing.append("task_id")
        if not evidence.get("commit_sha"):
            missing.append("commit_sha")
        if not evidence.get("diff_hash"):
            missing.append("diff_hash")
        if "changed_files" not in evidence:
            missing.append("changed_files")
        if not evidence.get("tests"):
            missing.append("tests")
        if evidence.get("reviewer") != ReviewDecision.APPROVED.value:
            missing.append("reviewer")
        if evidence.get("security") != ReviewDecision.APPROVED.value:
            missing.append("security")
        if not evidence.get("audit_checkpoint"):
            missing.append("audit_checkpoint")
        if evidence.get("audit_chain") is not True:
            missing.append("audit_chain")
        if not extras.gates_satisfied():
            missing.extend(f"gate:{gate.value}" for gate in sorted(extras.missing_gates(), key=lambda g: g.value))
        if missing:
            return EvidenceGateResult(EvidenceGateStatus.BLOCK, tuple(dict.fromkeys(missing)))
        return EvidenceGateResult(EvidenceGateStatus.PASS)
