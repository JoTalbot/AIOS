"""Lifecycle router foundation for AIOS runtime."""

class LifecycleRouter:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    def route(self, event):
        if self.coordinator:
            return self.coordinator.handle(event)
        return event
