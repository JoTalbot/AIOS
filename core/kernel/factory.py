"""Factory for constructing the new AIOS kernel stack."""


class KernelFactory:
    """Builds core services through the dependency container."""

    def __init__(self, container):
        self.container = container

    def create_kernel(self):
        kernel = self.container.resolve("kernel")
        agent_manager = self.container.resolve("agent_manager")
        bootstrap = self.container.resolve("bootstrap")

        bootstrap.agent_manager = agent_manager
        bootstrap.initialize()

        return kernel
