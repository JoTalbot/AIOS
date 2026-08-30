from dataclasses import dataclass, field
from typing import Dict

@dataclass
class TwinState:
    system_id: str
    metrics: Dict = field(default_factory=dict)
    resources: Dict = field(default_factory=dict)
    components: Dict = field(default_factory=dict)

    def update(self, values: Dict):
        self.metrics.update(values)
