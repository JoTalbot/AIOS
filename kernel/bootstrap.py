"""Kernel bootstrap wiring for the new event-driven architecture."""


class KernelBootstrap:
    """Connects lifecycle components during kernel initialization."""

    def __init__(self, kernel, agent_manager, event_hooks=None):
        self.kernel = kernel
        self.agent_manager = agent_manager
        self.event_hooks = event_hooks

    def initialize(self):
        if self.event_hooks is not None:
            self.event_hooks.attach()

        if hasattr(self.kernel, "agent_manager"):
            self.kernel.agent_manager = self.agent_manager

        return self.kernel

    def shutdown(self):
        if hasattr(self.agent_manager, "snapshot"):
            self.agent_manager.snapshot()
