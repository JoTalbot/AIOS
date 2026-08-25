"""Map capability metadata to deterministic architecture controls."""

from dataclasses import dataclass

from .capabilities import CapabilityDefinition


@dataclass(frozen=True)
class RiskControls:
    approval_required: bool
    audit_required: bool
    max_delegation_seconds: int


def controls_for(definition: CapabilityDefinition) -> RiskControls:
    if definition.risk == "critical":
        return RiskControls(True, True, 60)
    if definition.risk == "high":
        return RiskControls(True, True, 300)
    if definition.risk == "normal":
        return RiskControls(False, True, 900)
    return RiskControls(False, False, 3600)
