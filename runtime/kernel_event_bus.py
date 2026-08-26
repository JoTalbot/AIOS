"""AIOS internal event bus for subsystem communication."""


class KernelEventBus:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event, callback):
        self.listeners.setdefault(event, []).append(callback)

    def publish(self, event, payload=None):
        results = []
        for callback in self.listeners.get(event, []):
            results.append(callback(payload))
        return results
