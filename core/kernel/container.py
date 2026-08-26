"""Dependency wiring container for AIOS kernel components."""


class KernelContainer:
    """Minimal dependency registry used by bootstrap."""

    def __init__(self):
        self._services = {}

    def register(self, name, service):
        self._services[name] = service
        return service

    def resolve(self, name):
        return self._services.get(name)

    def build_bootstrap(self, kernel, agent_manager, event_hooks=None):
        from .bootstrap import KernelBootstrap

        self.register("kernel", kernel)
        self.register("agent_manager", agent_manager)
        if event_hooks is not None:
            self.register("event_hooks", event_hooks)

        return KernelBootstrap(
            kernel,
            agent_manager,
            event_hooks,
        )
