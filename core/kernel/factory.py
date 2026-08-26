"""Factory for constructing the new AIOS kernel stack."""


class KernelFactory:
    """Builds core services through the dependency container and registry."""

    def __init__(self, container, registry=None):
        self.container = container
        self.registry = registry

    def register_services(self):
        if not self.registry:
            return

        for name in self.container.list_services():
            component = self.container.resolve(name)
            self.registry.register(name, component)

    def wire_registry(self):
        if self.registry and hasattr(self.registry, "wire_container"):
            self.registry.wire_container(self.container)

    def create_runtime(self):
        self.register_services()
        self.wire_registry()

        bootstrap = self.container.resolve("bootstrap")
        if bootstrap:
            bootstrap.initialize()

        return {
            "kernel": self.container.resolve("kernel"),
            "agent_manager": self.container.resolve("agent_manager"),
            "bootstrap": bootstrap,
        }

    def create_kernel(self):
        runtime = self.create_runtime()
        return runtime["kernel"]
