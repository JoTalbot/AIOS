"""Runtime lifecycle hooks foundation for AIOS."""


class LifecycleHooks:
    def __init__(self):
        self._hooks = {}

    def register(self, event, callback):
        self._hooks.setdefault(event, []).append(callback)

    def emit(self, event, *args, **kwargs):
        for callback in self._hooks.get(event, []):
            callback(*args, **kwargs)
