class EventRuntime:
    """Connects AIOS runtime components through events."""

    def __init__(self, bus):
        self.bus = bus

    def agent_started(self, agent_id):
        return self.bus.publish(
            "agent.started",
            {"agent_id": agent_id},
        )

    def agent_finished(self, agent_id, result):
        return self.bus.publish(
            "agent.finished",
            {"agent_id": agent_id, "result": result},
        )
