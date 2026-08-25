"""Task-scoped, expiring delegation grants for supervisor specialists."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class DelegationGrant:
    grant_id: str
    owner_id: str
    delegated_by: str
    task_id: str
    role: str
    agent_id: str
    capabilities: frozenset[str]
    expires_at: datetime
    revoked: bool = False


class DelegationRegistry:
    """Issue, revoke, and validate narrowly scoped specialist grants."""

    def __init__(self) -> None:
        self.grants: dict[str, DelegationGrant] = {}

    def issue(
        self,
        *,
        owner_id: str,
        delegated_by: str,
        task_id: str,
        role: str,
        agent_id: str,
        capabilities: frozenset[str],
        expires_at: datetime,
    ) -> DelegationGrant:
        if expires_at.tzinfo is None:
            raise ValueError("delegation expiry must be timezone-aware")
        grant = DelegationGrant(
            grant_id=uuid4().hex,
            owner_id=owner_id,
            delegated_by=delegated_by,
            task_id=task_id,
            role=role,
            agent_id=agent_id,
            capabilities=capabilities,
            expires_at=expires_at,
        )
        self.grants[grant.grant_id] = grant
        return grant

    def revoke(self, grant_id: str) -> None:
        self.grants[grant_id].revoked = True

    def validate(
        self,
        grant_id: str,
        *,
        task_id: str,
        role: str,
        agent_id: str,
        capability: str,
        now: datetime | None = None,
    ) -> DelegationGrant:
        try:
            grant = self.grants[grant_id]
        except KeyError as exc:
            raise RuntimeError("delegation grant not found") from exc
        current = now or datetime.now(UTC)
        if grant.revoked:
            raise RuntimeError("delegation grant revoked")
        if current >= grant.expires_at:
            raise RuntimeError("delegation grant expired")
        if (grant.task_id, grant.role, grant.agent_id) != (task_id, role, agent_id):
            raise RuntimeError("delegation scope mismatch")
        if capability not in grant.capabilities:
            raise RuntimeError("delegation capability denied")
        return grant
