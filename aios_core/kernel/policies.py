"""Fail-closed capability and trust policy evaluation."""

from __future__ import annotations

from .decisions import PolicyDecision
from .identity import AgentIdentity

TRUST_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}


class PolicyEngine:
    """Evaluate explicit capability grants against identity and trust context."""

    def __init__(self) -> None:
        self.rules: dict[str, str] = {}

    def allow(self, capability: str, min_trust: str = "T0") -> None:
        """Allow a capability at or above *min_trust*."""
        if min_trust not in TRUST_RANK:
            raise ValueError(f"unknown trust level: {min_trust}")
        self.rules[capability] = min_trust

    def evaluate(
        self,
        capability: str,
        trust_level: str = "T0",
        identity: AgentIdentity | None = None,
    ) -> PolicyDecision:
        """Return an explicit decision; unknown inputs are denied."""
        agent_id = identity.agent_id if identity else ""
        required_trust = self.rules.get(capability)
        if required_trust is None:
            reason = "missing_policy_grant"
        elif identity is not None and not identity.has_capability(capability):
            reason = "identity_missing_capability"
        elif trust_level not in TRUST_RANK:
            reason = "unknown_trust_level"
        elif TRUST_RANK[trust_level] < TRUST_RANK[required_trust]:
            reason = "insufficient_trust"
        else:
            return PolicyDecision(True, "allowed", agent_id, capability, trust_level)
        return PolicyDecision(False, reason, agent_id, capability, trust_level)
