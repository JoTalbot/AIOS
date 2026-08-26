"""AIOS runtime configuration foundation."""

class RuntimeConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)
