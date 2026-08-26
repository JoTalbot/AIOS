"""Agent lifecycle manager."""

from .runtime import AgentRuntime


class AgentManager:
    def __init__(self):
        self.agents = {}
        self.runtimes = {}

    def register(self, agent):
        self.agents[agent.name] = agent
        self.runtimes[agent.name] = AgentRuntime(agent)

    def get(self, name):
        return self.agents.get(name)

    def get_runtime(self, name):
        return self.runtimes.get(name)

    def start(self, name):
        runtime = self.get_runtime(name)
        return runtime.start() if runtime else None

    def stop(self, name):
        runtime = self.get_runtime(name)
        return runtime.stop() if runtime else None

    def execute(self, name, request):
        runtime = self.get_runtime(name)
        return runtime.execute(request) if runtime else None
