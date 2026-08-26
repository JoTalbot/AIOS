"""Execution state persistence foundation."""


class StateStore:
    def __init__(self):
        self._states = {}

    def save(self, key, value):
        self._states[key] = dict(value) if isinstance(value, dict) else value

    def load(self, key):
        value = self._states.get(key)
        return dict(value) if isinstance(value, dict) else value

    def delete(self, key):
        self._states.pop(key, None)


class AgentStateStore(StateStore):
    """Agent-specific state persistence API."""

    def save_agent_state(self, agent_id, state):
        self.save(agent_id, state)

    def load_agent_state(self, agent_id):
        return self.load(agent_id)
