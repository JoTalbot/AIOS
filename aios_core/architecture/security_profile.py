"""Integrated control profile derived from registered capability risk."""

from __future__ import annotations

from dataclasses import dataclass

from .approval import ApprovalGate
from .capabilities import CapabilityDefinition, CapabilityRegistry
from .risk import RiskControls, controls_for


@dataclass(frozen=True)
class ArchitectureSecurityProfile:
    registry: CapabilityRegistry
    approval: ApprovalGate
    controls: dict[str, RiskControls]

    @classmethod
    def build(cls, definitions: tuple[CapabilityDefinition, ...]) -> ArchitectureSecurityProfile:
        registry = CapabilityRegistry()
        controls: dict[str, RiskControls] = {}
        approval_required: set[str] = set()
        for definition in definitions:
            registry.register(definition)
            control = controls_for(definition)
            controls[definition.name] = control
            if control.approval_required:
                approval_required.add(definition.name)
        return cls(registry, ApprovalGate(frozenset(approval_required)), controls)
