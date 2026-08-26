"""AIOS v22.5 Agent State Manager."""


class AgentStateManager:
    def __init__(self):
        self.state = {}

    def set_state(self, key, value):
        self.state[key] = value

    def get_state(self, key, default=None):
        return self.state.get(key, default)

    def snapshot(self):
        return dict(self.state)
