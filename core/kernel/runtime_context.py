"""Runtime context for the AIOS kernel stack."""

from .runtime_lifecycle import RuntimeLifecycle
from .restart_manager import RestartManager


class RuntimeContext:
    """Single object carrying wired kernel services."""

    def __init__(self, kernel=None, agent_manager=None, bootstrap=None, registry=None):
        self.kernel = kernel
        self.agent_manager = agent_manager
        self.bootstrap = bootstrap
        self.registry = registry
        self.lifecycle = RuntimeLifecycle(self)
        self.restart_manager = RestartManager(self)

    def services(self):
        return {
            "kernel": self.kernel,
            "agent_manager": self.agent_manager,
            "bootstrap": self.bootstrap,
            "registry": self.registry,
        }

    def start(self):
        return self.lifecycle.start()

    def stop(self):
        return self.lifecycle.stop()

    def restart(self):
        return self.restart_manager.restart()
