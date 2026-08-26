"""Runtime context for the AIOS kernel stack."""


class RuntimeContext:
    """Single object carrying wired kernel services."""

    def __init__(self, kernel=None, agent_manager=None, bootstrap=None, registry=None):
        self.kernel = kernel
        self.agent_manager = agent_manager
        self.bootstrap = bootstrap
        self.registry = registry

    def services(self):
        return {
            "kernel": self.kernel,
            "agent_manager": self.agent_manager,
            "bootstrap": self.bootstrap,
            "registry": self.registry,
        }
