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

    def create_kernel(self):
        self.register_services()

        kernel = self.container.resolve("kernel")
        agent_manager = self.container.resolve("agent_manager")
        bootstrap = self.container.resolve("bootstrap")

        bootstrap.agent_manager = agent_manager
        bootstrap.initialize()

        return kernel
