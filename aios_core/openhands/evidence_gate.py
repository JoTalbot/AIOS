"""Fail-closed completion gate with execution- and CI-bound evidence."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .models import ReviewDecision, TaskExtras


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

    REQUIRED = (
        "task_id", "commit_sha", "diff_hash", "changed_files", "tests",
        "reviewer", "security", "audit_checkpoint", "audit_chain",
        "test_commit_binding", "test_diff_binding", "evidence_commit_binding",
        "evidence_diff_binding", "ci_run_binding", "ci_job_binding",
        "ci_required_workflows_success",
    )

    def evaluate(self, extras: TaskExtras, evidence: Mapping[str, Any] | None = None) -> EvidenceGateResult:
        evidence = evidence or {}
        missing: list[str] = []
        if not extras.task_id:
            missing.append("task_id")
        commit_sha = evidence.get("commit_sha")
        diff_hash = evidence.get("diff_hash")
        if not commit_sha:
            missing.append("commit_sha")
        if not diff_hash:
            missing.append("diff_hash")
        if "changed_files" not in evidence:
            missing.append("changed_files")
        if evidence.get("tests") is not True:
            missing.append("tests")
        if evidence.get("test_commit_sha") != commit_sha:
            missing.append("test_commit_binding")
        if evidence.get("test_diff_hash") != diff_hash:
            missing.append("test_diff_binding")
        if evidence.get("reviewer") != ReviewDecision.APPROVED.value:
            missing.append("reviewer")
        if evidence.get("security") != ReviewDecision.APPROVED.value:
            missing.append("security")
        if not evidence.get("audit_checkpoint"):
            missing.append("audit_checkpoint")
        if evidence.get("audit_chain") is not True:
            missing.append("audit_chain")
        if evidence.get("evidence_commit_sha") != commit_sha:
            missing.append("evidence_commit_binding")
        if evidence.get("evidence_diff_hash") != diff_hash:
            missing.append("evidence_diff_binding")

        ci_run_id = evidence.get("ci_run_id")
        ci_job_id = evidence.get("ci_job_id")
        ci_commit_sha = evidence.get("ci_commit_sha")
        ci_conclusion = evidence.get("ci_conclusion")
        if not ci_run_id or ci_commit_sha != commit_sha or ci_conclusion != "success":
            missing.append("ci_run_binding")
        if not ci_job_id:
            missing.append("ci_job_binding")
        if evidence.get("ci_required_workflows_success") is not True:
            missing.append("ci_required_workflows_success")

        if not extras.gates_satisfied():
            missing.extend(f"gate:{gate.value}" for gate in sorted(extras.missing_gates(), key=lambda g: g.value))
        if missing:
            return EvidenceGateResult(EvidenceGateStatus.BLOCK, tuple(dict.fromkeys(missing)))
        return EvidenceGateResult(EvidenceGateStatus.PASS)
