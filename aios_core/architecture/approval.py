"""One-shot human approval state for high-risk architecture actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSUMED = "consumed"


@dataclass
class ApprovalRequest:
    action_id: str
    task_id: str
    agent_id: str
    capability: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None
    decided_at: str | None = None


class ApprovalGate:
    """Require and consume explicit approval for configured capabilities."""

    def __init__(self, required_capabilities: frozenset[str] = frozenset()) -> None:
        self.required_capabilities = required_capabilities
        self.requests: dict[str, ApprovalRequest] = {}

    def requires(self, capability: str) -> bool:
        return capability in self.required_capabilities

    def request(self, *, action_id: str, task_id: str, agent_id: str, capability: str) -> ApprovalRequest:
        request = self.requests.get(action_id)
        if request is None:
            request = ApprovalRequest(action_id, task_id, agent_id, capability)
            self.requests[action_id] = request
        return request

    def decide(self, action_id: str, *, approved: bool, decided_by: str) -> ApprovalRequest:
        request = self.requests[action_id]
        if request.status is not ApprovalStatus.PENDING:
            raise RuntimeError(f"approval is already {request.status}")
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.decided_by = decided_by
        request.decided_at = datetime.now(UTC).isoformat()
        return request

    def consume(self, action_id: str) -> bool:
        request = self.requests.get(action_id)
        if request is None or request.status is not ApprovalStatus.APPROVED:
            return False
        request.status = ApprovalStatus.CONSUMED
        return True
