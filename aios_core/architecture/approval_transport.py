"""Authenticated, replay-resistant commands for human approval decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .approval import ApprovalGate, ApprovalRequest
from .signing import HMACSigner


@dataclass(frozen=True)
class ApprovalCommand:
    action_id: str
    approved: bool
    decided_by: str
    timestamp: str
    nonce: str
    key_id: str
    signature: str = ""

    def payload(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("signature")
        return data


class ApprovalCommandVerifier:
    def __init__(self, signers: dict[str, HMACSigner], max_age_seconds: float = 300) -> None:
        self.signers = signers
        self.max_age_seconds = max_age_seconds
        self.used_nonces: set[str] = set()

    def apply(self, command: ApprovalCommand, gate: ApprovalGate, *, now: datetime | None = None) -> ApprovalRequest:
        signer = self.signers.get(command.key_id)
        if signer is None or not signer.verify(command.payload(), command.signature):
            raise RuntimeError("approval signature invalid")
        current = now or datetime.now(UTC)
        issued = datetime.fromisoformat(command.timestamp)
        if issued.tzinfo is None or abs((current - issued).total_seconds()) > self.max_age_seconds:
            raise RuntimeError("approval command stale")
        if command.nonce in self.used_nonces:
            raise RuntimeError("approval command replayed")
        self.used_nonces.add(command.nonce)
        return gate.decide(command.action_id, approved=command.approved, decided_by=command.decided_by)
