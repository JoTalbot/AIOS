"""Lifecycle controller for RuntimeContext."""


class RuntimeLifecycle:
    """Controls startup and shutdown of the assembled runtime context."""

    def __init__(self, context):
        self.context = context

    def start(self):
        manager = self.context.agent_manager
        if manager and hasattr(manager, "recover"):
            manager.recover()

        if self.context.bootstrap:
            self.context.bootstrap.initialize()
        return self.context

    def stop(self):
        manager = self.context.agent_manager
        if manager and hasattr(manager, "snapshot"):
            manager.snapshot()

        if self.context.bootstrap and hasattr(self.context.bootstrap, "shutdown"):
            self.context.bootstrap.shutdown()
        return self.context
