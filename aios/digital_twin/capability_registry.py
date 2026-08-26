"""Registry of capabilities exposed by a Digital Twin."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CapabilityRegistry:
    capabilities: Dict[str, Dict] = field(default_factory=dict)

    def register(self, name: str, metadata: Dict | None = None) -> None:
        self.capabilities[name] = metadata or {}

    def supports(self, name: str) -> bool:
        return name in self.capabilities

    def list(self) -> List[str]:
        return sorted(self.capabilities)
