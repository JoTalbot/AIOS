from collections import defaultdict


class EventBus:
    """Central event dispatcher for AIOS components."""

    def __init__(self):
        self.handlers = defaultdict(list)

    def subscribe(self, event, handler):
        self.handlers[event].append(handler)

    def publish(self, event, payload=None):
        results = []
        for handler in self.handlers[event]:
            results.append(handler(payload))
        return results
