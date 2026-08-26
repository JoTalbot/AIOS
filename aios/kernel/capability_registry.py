"""AIOS v20 Capability Registry foundation.

Registry boundary between agents and executable capabilities.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    name: str
    description: str = ""


class CapabilityRegistry:
    """Discoverable capability storage for AIOS agents."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def list(self) -> list[Capability]:
        return list(self._capabilities.values())
