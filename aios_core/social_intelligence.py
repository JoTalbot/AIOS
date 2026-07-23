"""Social Intelligence for AIOS"""

from typing import Dict, List


class SocialIntelligence:
    """Social reasoning and interaction."""

    def __init__(self):
        self.relationships: Dict[str, Dict] = {}
        self.norms: List[str] = ["cooperation", "fairness", "reciprocity"]

    def update_relationship(self, agent_a: str, agent_b: str, interaction: Dict):
        key = f"{agent_a}_{agent_b}"
        self.relationships[key] = interaction

    def social_reasoning(self, context: Dict) -> List[str]:
        return ["cooperate", "communicate"]

    def stats(self) -> dict:
        return {"relationships": len(self.relationships), "norms": len(self.norms)}
