"""Deterministic architecture security health snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from .approval import ApprovalGate, ApprovalStatus
from .audit import ArchitectureAuditStore
from .delegation import DelegationRegistry


@dataclass(frozen=True)
class ArchitectureHealth:
    healthy: bool
    audit_valid: bool
    pending_approvals: int
    revoked_grants: int


def architecture_health(
    *, audit: ArchitectureAuditStore | None, approval: ApprovalGate | None, delegations: DelegationRegistry | None
) -> ArchitectureHealth:
    audit_valid = audit is None or audit.verify()
    pending = 0 if approval is None else sum(r.status is ApprovalStatus.PENDING for r in approval.requests.values())
    revoked = 0 if delegations is None else sum(grant.revoked for grant in delegations.grants.values())
    return ArchitectureHealth(audit_valid and pending == 0, audit_valid, pending, revoked)
