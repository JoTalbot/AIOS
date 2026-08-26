"""Runtime metrics foundation."""


class RuntimeMetrics:
    def __init__(self):
        self.counters = {}

    def increment(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1

    def snapshot(self):
        return dict(self.counters)
