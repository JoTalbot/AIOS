from dataclasses import dataclass
from enum import Enum


class DecisionStatus(Enum):
    ALLOW = "allow"
    ALLOW_WITH_CONSTRAINTS = "allow_with_constraints"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyDecision:
    status: DecisionStatus
    reason: str
    constraints: list[str]


class PolicyEngine:
    def evaluate(self, request, capabilities=None):
        if capabilities is None:
            capabilities = []

        if request.capability not in capabilities:
            return PolicyDecision(
                DecisionStatus.DENY,
                "Capability not granted",
                []
            )

        return PolicyDecision(
            DecisionStatus.ALLOW,
            "Policy checks passed",
            []
        )
