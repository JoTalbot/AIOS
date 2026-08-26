class WeightedVote:
    def __init__(self, agent_id: str, action: str, confidence: float, weight: float = 1.0):
        self.agent_id = agent_id
        self.action = action
        self.confidence = confidence
        self.weight = weight

    @property
    def score(self):
        return self.confidence * self.weight


class WeightedConsensusEngine:
    def aggregate(self, votes):
        scores = {}
        for vote in votes:
            scores[vote.action] = scores.get(vote.action, 0.0) + vote.score

        if not scores:
            return None

        action = max(scores, key=scores.get)
        return {
            "action": action,
            "score": scores[action],
        }
