from dataclasses import dataclass, field
from typing import Dict

@dataclass
class NodeIdentity:
    node_id: str
    public_key: str = ""

@dataclass
class FederationSecurity:
    identities: Dict[str, NodeIdentity] = field(default_factory=dict)
    trust_scores: Dict[str, float] = field(default_factory=dict)
    audit_history: list = field(default_factory=list)

    def verify_node(self, node_id: str) -> bool:
        return node_id in self.identities

    def audit(self, event: str):
        self.audit_history.append(event)
