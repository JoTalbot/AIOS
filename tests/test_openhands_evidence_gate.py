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
        "reviewer": ReviewDecision.APPROVED.value,
        "security": ReviewDecision.APPROVED.value,
        "audit_checkpoint": True,
        "audit_chain": True,
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
    assert not result.allowed


def test_unapproved_security_blocks_completion():
    evidence = passing_evidence()
    evidence["security"] = ReviewDecision.CHANGES_REQUESTED.value
    result = EvidenceGate().evaluate(passing_extras(), evidence)
    assert result.status == EvidenceGateStatus.BLOCK
    assert "security" in result.missing
