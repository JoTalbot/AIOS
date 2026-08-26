"""AIOS system health monitoring."""


class SystemMonitor:
    def __init__(self):
        self.components = {}

    def register(self, name, status="unknown"):
        self.components[name] = status

    def update(self, name, status):
        self.components[name] = status

    def health(self):
        return dict(self.components)
