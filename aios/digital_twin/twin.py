from dataclasses import dataclass, field
from typing import Dict

@dataclass
class DigitalTwin:
    twin_id: str
    system_state: Dict = field(default_factory=dict)
    simulations: list = field(default_factory=list)

    def snapshot(self, state: Dict):
        self.system_state = state

    def simulate(self, scenario: Dict):
        self.simulations.append(scenario)
        return scenario
