class AgentTrustManager:
    def __init__(self):
        self.scores = {}

    def update(self, agent_id, score):
        self.scores[agent_id] = score

    def get_trust(self, agent_id):
        return self.scores.get(agent_id, 0)
