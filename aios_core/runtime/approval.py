"""Explicit approval queue for policy-gated AIOS actions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from .contracts import AgentTask


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    task_id: str
    permission: str
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None


class ApprovalQueue:
    """In-memory approval queue with explicit state transitions."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def request(self, task: AgentTask, permission: str, reason: str) -> ApprovalRequest:
        item = ApprovalRequest(uuid4().hex, task.task_id, permission, reason)
        self._requests[item.request_id] = item
        return item

    def get(self, request_id: str) -> ApprovalRequest:
        return self._requests[request_id]

    def decide(self, request_id: str, *, approved: bool, decided_by: str) -> ApprovalRequest:
        current = self.get(request_id)
        if current.status is not ApprovalStatus.PENDING:
            raise ValueError("approval request is no longer pending")
        updated = ApprovalRequest(
            request_id=current.request_id,
            task_id=current.task_id,
            permission=current.permission,
            reason=current.reason,
            status=ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
            decided_by=decided_by,
        )
        self._requests[request_id] = updated
        return updated

    def pending(self) -> tuple[ApprovalRequest, ...]:
        return tuple(item for item in self._requests.values() if item.status is ApprovalStatus.PENDING)
