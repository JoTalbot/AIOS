"""AIOS v20 runtime adapter boundary."""


class RuntimeAdapter:
    """Compatibility bridge between v20 kernel and existing runtime."""

    def __init__(self, runtime=None):
        self.runtime = runtime

    def execute(self, intent):
        if self.runtime and hasattr(self.runtime, "execute"):
            return self.runtime.execute(intent)
        return {"status": "planned", "intent": intent}
