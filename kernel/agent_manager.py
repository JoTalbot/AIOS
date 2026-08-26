class AgentManager:
    def __init__(self, memory, bus, sandbox):
        self.memory = memory
        self.bus = bus
        self.sandbox = sandbox
        self.agents = {}

    def register(self, agent):
        self.agents[agent.agent_id] = agent

    async def start(self, agent_id, goal):
        agent = self.agents[agent_id]
        return await agent.run(goal)

    def list_agents(self):
        return list(self.agents.keys())
