from aios_core.openhands.evidence_gate import EvidenceGate, EvidenceGateStatus
from aios_core.openhands.models import Gate, ReviewDecision, TaskExtras


def passing_extras():
    extras = TaskExtras(task_id="task-1", required_gates=frozenset({Gate.TESTS, Gate.REVIEW, Gate.SECURITY_REVIEW}))
    extras.passed_gates = frozenset(extras.required_gates)
    return extras


def passing_evidence():
    return {
        "commit_sha": "a" * 40,
        "diff_hash": "b" * 64,
        "changed_files": ["aios_core/openhands/evidence_gate.py"],
        "tests": True,
        "test_commit_sha": "a" * 40,
        "test_diff_hash": "b" * 64,
        "reviewer": ReviewDecision.APPROVED.value,
        "security": ReviewDecision.APPROVED.value,
        "audit_checkpoint": True,
        "audit_chain": True,
        "evidence_commit_sha": "a" * 40,
        "evidence_diff_hash": "b" * 64,
    }


def test_complete_requires_all_evidence():
    result = EvidenceGate().evaluate(passing_extras(), passing_evidence())
    assert result.status == EvidenceGateStatus.PASS
    assert result.allowed


def test_missing_evidence_blocks_completion():
    evidence = passing_evidence()
    evidence.pop("diff_hash")
    result = EvidenceGate().evaluate(passing_extras(), evidence)
    assert result.status == EvidenceGateStatus.BLOCK
    assert "diff_hash" in result.missing


def test_unapproved_security_blocks_completion():
    evidence = passing_evidence()
    evidence["security"] = ReviewDecision.CHANGES_REQUESTED.value
    result = EvidenceGate().evaluate(passing_extras(), evidence)
    assert result.status == EvidenceGateStatus.BLOCK
    assert "security" in result.missing


def test_old_test_commit_cannot_authorize_new_commit():
    evidence = passing_evidence()
    evidence["test_commit_sha"] = "c" * 40
    result = EvidenceGate().evaluate(passing_extras(), evidence)
    assert result.status == EvidenceGateStatus.BLOCK
    assert "test_commit_binding" in result.missing


def test_old_test_diff_cannot_authorize_new_diff():
    evidence = passing_evidence()
    evidence["test_diff_hash"] = "d" * 64
    result = EvidenceGate().evaluate(passing_extras(), evidence)
    assert result.status == EvidenceGateStatus.BLOCK
    assert "test_diff_binding" in result.missing


def test_evidence_identity_must_match_current_git_state():
    evidence = passing_evidence()
    evidence["evidence_diff_hash"] = "e" * 64
    result = EvidenceGate().evaluate(passing_extras(), evidence)
    assert result.status == EvidenceGateStatus.BLOCK
    assert "evidence_diff_binding" in result.missing
