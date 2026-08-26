class AgentLearningState:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.score = 0.0
        self.updates = 0

    def update(self, reward):
        self.score += reward
        self.updates += 1


class MultiAgentAdaptiveLearning:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_id):
        self.agents[agent_id] = AgentLearningState(agent_id)

    def update_agent(self, agent_id, reward):
        if agent_id in self.agents:
            self.agents[agent_id].update(reward)

    def collective_score(self):
        return sum(agent.score for agent in self.agents.values())
