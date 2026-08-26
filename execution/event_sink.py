"""Small protocol/adapter for execution event delivery."""

from collections.abc import Callable


class ExecutionEventSink:
    """Deliver canonical execution events to a callable or recorder."""

    def __init__(self, target=None):
        self.target = target

    def attach(self, target):
        self.target = target
        return target

    def emit(self, event):
        if self.target is None:
            return None
        if callable(self.target):
            return self.target(event)
        if hasattr(self.target, "record"):
            return self.target.record(event)
        raise TypeError("execution event target must be callable or expose record()")
