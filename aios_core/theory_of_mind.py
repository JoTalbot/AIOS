"""Theory of Mind for AIOS Agents"""

from typing import Dict, List


class TheoryOfMind:
    """Model of other agents' mental states."""

    def __init__(self):
        self.models: Dict[str, Dict] = {}

    def model_agent(
        self, agent_id: str, beliefs: Dict, desires: List, intentions: List
    ):
        self.models[agent_id] = {
            "beliefs": beliefs,
            "desires": desires,
            "intentions": intentions,
        }

    def predict_action(self, agent_id: str, situation: Dict) -> str:
        model = self.models.get(agent_id, {})
        if "harm" in str(situation):
            return "avoid"
        return "cooperate"

    def stats(self) -> dict:
        return {"modeled_agents": len(self.models)}
