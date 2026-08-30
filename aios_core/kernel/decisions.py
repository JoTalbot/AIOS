from dataclasses import dataclass


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
