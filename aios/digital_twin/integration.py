"""Dependency-free integration coordinator for Digital Twin subsystems."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TwinIntegration:
    components: List[str] = field(default_factory=list)
    state: Dict = field(default_factory=dict)

    def register(self, component: str) -> None:
        if component not in self.components:
            self.components.append(component)

    def publish_state(self, state: Dict) -> None:
        self.state = dict(state)

    def status(self) -> Dict:
        return {"components": sorted(self.components), "state": dict(self.state)}
