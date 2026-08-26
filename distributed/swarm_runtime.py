import asyncio


class SwarmRuntime:
    def __init__(self):
        self.agents = {}

    def register(self, agent_id, agent):
        self.agents[agent_id] = agent

    async def broadcast(self, goal):
        results = []
        for agent in self.agents.values():
            results.append(await agent.run(goal))
        return results
