class AgentTrustState:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.trust_score = 0.0
        self.updates = 0

    def update(self, feedback):
        self.trust_score += feedback
        self.updates += 1


class MultiAgentTrustLearning:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_id):
        self.agents[agent_id] = AgentTrustState(agent_id)

    def update_trust(self, agent_id, feedback):
        if agent_id not in self.agents:
            self.register_agent(agent_id)
        self.agents[agent_id].update(feedback)

    def get_trust_score(self, agent_id):
        state = self.agents.get(agent_id)
        return state.trust_score if state else 0.0
