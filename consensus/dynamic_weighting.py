"""Dynamic consensus weighting for AIOS agents.

Combines agent evaluation scores with consensus voting confidence.
"""


class AgentWeight:
    def __init__(self, agent_id: str, weight: float):
        self.agent_id = agent_id
        self.weight = weight


class DynamicConsensusWeighting:
    def __init__(self):
        self.weights = {}

    def update_weight(self, agent_id: str, evaluation_score: float):
        self.weights[agent_id] = max(0.0, min(1.0, evaluation_score))

    def apply(self, votes):
        weighted = []
        for vote in votes:
            weight = self.weights.get(vote.agent_id, 0.5)
            weighted.append((vote, vote.confidence * weight))
        return weighted
