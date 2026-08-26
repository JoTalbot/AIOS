"""Execution state persistence foundation."""


class StateStore:
    def __init__(self):
        self._states = {}
        self._versions = {}

    def save(self, key, value, version=1):
        self._states[key] = dict(value) if isinstance(value, dict) else value
        self._versions[key] = version

    def load(self, key):
        value = self._states.get(key)
        return dict(value) if isinstance(value, dict) else value

    def version(self, key):
        return self._versions.get(key, 1)

    def delete(self, key):
        self._states.pop(key, None)
        self._versions.pop(key, None)


class AgentStateStore(StateStore):
    """Agent-specific state persistence API."""

    def save_agent_state(self, agent_id, state, version=1):
        self.save(agent_id, state, version=version)

    def load_agent_state(self, agent_id):
        return self.load(agent_id)

    def migrate(self, agent_id, target_version, handler):
        current = self.version(agent_id)
        if current < target_version:
            state = handler(self.load(agent_id), current, target_version)
            self.save(agent_id, state, version=target_version)
        return self.load(agent_id)
