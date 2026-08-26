"""Agent lifecycle manager."""

from .runtime import AgentRuntime


class AgentManager:
    def __init__(self, event_bus=None):
        self.agents = {}
        self.runtimes = {}
        self.event_bus = event_bus

    def _publish(self, name, payload):
        if self.event_bus:
            self.event_bus.publish(name, payload, source="agent_manager")

    def register(self, agent):
        self.agents[agent.name] = agent
        self.runtimes[agent.name] = AgentRuntime(agent, event_bus=self.event_bus)
        self._publish("agent.registered", {"agent": agent.name})

    def get(self, name):
        return self.agents.get(name)

    def get_runtime(self, name):
        return self.runtimes.get(name)

    def start(self, name):
        runtime = self.get_runtime(name)
        result = runtime.start() if runtime else None
        if result:
            self._publish("agent.started", {"agent": name})
        return result

    def stop(self, name):
        runtime = self.get_runtime(name)
        result = runtime.stop() if runtime else None
        if result:
            self._publish("agent.stopped", {"agent": name})
        return result

    def execute(self, name, request):
        runtime = self.get_runtime(name)
        return runtime.execute(request) if runtime else None
