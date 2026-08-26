"""Execution persistence foundation."""

class ExecutionStore:
    def __init__(self):
        self._states = {}

    def save(self, key, value):
        self._states[key] = value

    def load(self, key):
        return self._states.get(key)
