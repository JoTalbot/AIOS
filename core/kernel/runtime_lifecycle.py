"""Lifecycle controller for RuntimeContext."""


class RuntimeLifecycle:
    """Controls startup and shutdown of the assembled runtime context."""

    def __init__(self, context):
        self.context = context

    def start(self):
        if self.context.bootstrap:
            self.context.bootstrap.initialize()
        return self.context

    def stop(self):
        if self.context.bootstrap and hasattr(self.context.bootstrap, "shutdown"):
            self.context.bootstrap.shutdown()
        return self.context
