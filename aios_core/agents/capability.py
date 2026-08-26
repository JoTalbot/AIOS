"""AIOS Agent Capability System.

Provides capability declarations and task compatibility checks.
"""

from dataclasses import dataclass, field
from typing import Set


@dataclass
class Capability:
    name: str
    version: str = "1.0"
    actions: Set[str] = field(default_factory=set)

    def supports(self, action: str) -> bool:
        return action in self.actions or "*" in self.actions


class CapabilityRegistry:
    def __init__(self):
        self._capabilities = {}

    def register(self, capability: Capability):
        self._capabilities[capability.name] = capability

    def get(self, name: str):
        return self._capabilities.get(name)

    def can_execute(self, capability_name: str, action: str) -> bool:
        capability = self.get(capability_name)
        return capability.supports(action) if capability else False
