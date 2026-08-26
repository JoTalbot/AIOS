class AgentSwarm:
    def __init__(self):
        self.agents = {}

    def register(self, agent):
        self.agents[agent.id] = agent

    async def broadcast(self, task):
        results = []
        for agent in self.agents.values():
            results.append(await agent.run(task))
        return results
