"""AIOS v23.9 Consensus Engine.

Provides a lightweight consensus mechanism for swarm decisions.
"""


class ConsensusEngine:
    def __init__(self):
        self.decisions = []

    def submit(self, agent_id, decision, confidence=0.0):
        self.decisions.append({
            "agent_id": agent_id,
            "decision": decision,
            "confidence": confidence,
        })

    def resolve(self):
        if not self.decisions:
            return None
        return max(self.decisions, key=lambda item: item["confidence"])
