from time import time


class HealthMonitor:
    def __init__(self):
        self.history = []

    def check(self, components=None):
        snapshot = {
            "timestamp": time(),
            "status": "ok",
            "components": components or {}
        }
        self.history.append(snapshot)
        return snapshot

    def last(self):
        return self.history[-1] if self.history else None
