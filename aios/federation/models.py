from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class FederationNode:
    node_id: str
    capabilities: List[str] = field(default_factory=list)
    trust_score: float = 0.0
    resources: Dict = field(default_factory=dict)

@dataclass
class Federation:
    federation_id: str
    nodes: List[FederationNode] = field(default_factory=list)
    topology: Dict = field(default_factory=dict)
    policies: Dict = field(default_factory=dict)
    trust_network: Dict = field(default_factory=dict)
