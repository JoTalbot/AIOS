"""Execution state persistence foundation with adaptive recovery policy."""


class StateStore:
    def __init__(self):
        self._states = {}
        self._versions = {}
        self._checkpoints = {}
        self._health = {}
        self._policies = {}

    def save(self, key, value, version=1):
        self._states[key] = dict(value) if isinstance(value, dict) else value
        self._versions[key] = version
        self.mark_healthy(key)

    def load(self, key):
        value = self._states.get(key)
        return dict(value) if isinstance(value, dict) else value

    def version(self, key):
        return self._versions.get(key, 1)

    def delete(self, key):
        self._states.pop(key, None)
        self._versions.pop(key, None)
        self._checkpoints.pop(key, None)
        self._health.pop(key, None)
        self._policies.pop(key, None)

    def checkpoint(self, key):
        self._checkpoints[key] = self.load(key)
        return self.load(key)

    def rollback(self, key):
        if key in self._checkpoints:
            self.save(key, self._checkpoints[key], version=self.version(key))
        return self.load(key)

    def mark_failed(self, key, reason=None):
        self._health[key] = {"status": "failed", "reason": reason}

    def mark_healthy(self, key):
        self._health[key] = {"status": "healthy"}

    def health(self, key):
        return self._health.get(key, {"status": "unknown"})

    def set_policy(self, key, policy):
        self._policies[key] = dict(policy)

    def policy(self, key):
        return dict(self._policies.get(key, {"retries": 0, "rollback": True}))


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

    def checkpoint_agent(self, agent_id):
        return self.checkpoint(agent_id)

    def rollback_agent(self, agent_id):
        return self.rollback(agent_id)
