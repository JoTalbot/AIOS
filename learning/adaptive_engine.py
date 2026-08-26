class AdaptiveEngine:
    def __init__(self, memory=None):
        self.memory = memory
        self.metrics = {}

    def record_experience(self, agent_id, experience):
        self.metrics.setdefault(agent_id, []).append(experience)

        if self.memory:
            self.memory.remember(agent_id, experience)

    def improve(self, agent_id):
        history = self.metrics.get(agent_id, [])
        return {
            "agent": agent_id,
            "experiences": len(history),
            "status": "adapted"
        }
