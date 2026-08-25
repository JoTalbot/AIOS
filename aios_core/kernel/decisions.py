"""Immutable decisions produced by the v20 policy engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    """Auditable result of one capability authorization request."""

    allowed: bool
    reason: str
    agent_id: str = ""
    capability: str = ""
    trust_level: str = "T0"
