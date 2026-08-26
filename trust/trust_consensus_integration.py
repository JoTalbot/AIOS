class TrustConsensusContext:
    def __init__(self, agent_id, trust_score):
        self.agent_id = agent_id
        self.trust_score = trust_score


class TrustConsensusIntegration:
    def __init__(self):
        self.weights = {}

    def update_agent_trust(self, agent_id, trust_score):
        self.weights[agent_id] = trust_score

    def get_consensus_weight(self, agent_id):
        return self.weights.get(agent_id, 0.0)

    def rank_agents(self):
        return sorted(self.weights.items(), key=lambda item: item[1], reverse=True)
