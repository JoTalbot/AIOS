"""
AIOS Trust Manager Layer v2.1.1

Manages trust evaluation for AIOS agents.
"""


class TrustManager:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_id: str, score: float = 0.0):
        self.agents[agent_id] = score
        return {"agent_id": agent_id, "trust_score": score}

    def evaluate(self, agent_id: str):
        return {
            "agent_id": agent_id,
            "trust_score": self.agents.get(agent_id, 0.0)
        }
