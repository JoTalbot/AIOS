class AgentSimulationResult:
    def __init__(self, agent_id, action, reward):
        self.agent_id = agent_id
        self.action = action
        self.reward = reward


class MultiAgentSimulation:
    def __init__(self, agents=None):
        self.agents = agents or []
        self.results = []

    def run_cycle(self, context):
        for agent in self.agents:
            action = agent.decide(context)
            result = AgentSimulationResult(
                agent_id=agent.id,
                action=action,
                reward=0.0,
            )
            self.results.append(result)
        return self.results
