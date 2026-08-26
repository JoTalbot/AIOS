"""AIOS v23.7 Shared Agent Memory Layer."""

class SharedAgentMemory:
    def __init__(self):
        self.memory = {}

    def store(self, agent_id, key, value):
        self.memory.setdefault(agent_id, {})[key] = value

    def recall(self, agent_id, key=None):
        if key is None:
            return self.memory.get(agent_id, {})
        return self.memory.get(agent_id, {}).get(key)
