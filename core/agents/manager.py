"""Agent lifecycle manager."""

from .runtime import AgentRuntime, AgentRuntimeState


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

    def unregister(self, name):
        runtime = self.runtimes.pop(name, None)
        self.agents.pop(name, None)
        self._publish("agent.unregistered", {"agent": name})
        return runtime

    def get(self, name):
        return self.agents.get(name)

    def get_runtime(self, name):
        return self.runtimes.get(name)

    def snapshot(self):
        return {
            name: runtime.state.value
            for name, runtime in self.runtimes.items()
        }

    def recover(self, snapshot):
        for name, state in snapshot.items():
            runtime = self.get_runtime(name)
            if not runtime:
                continue
            if state == AgentRuntimeState.RUNNING.value:
                runtime.start()
            elif state == AgentRuntimeState.STOPPED.value:
                runtime.stop()

        self._publish("agent.recovered", snapshot)
        return self.snapshot()

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
