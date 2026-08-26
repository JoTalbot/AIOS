"""Runtime context for the AIOS kernel stack."""

from .runtime_lifecycle import RuntimeLifecycle
from .restart_manager import RestartManager
from .restart_events import RestartEventEmitter
from .runtime_context_persistence import RuntimeContextPersistence


class RuntimeContext:
    """Single object carrying wired kernel services."""

    def __init__(self, kernel=None, agent_manager=None, bootstrap=None, registry=None, event_bus=None, persistence=None):
        self.kernel = kernel
        self.agent_manager = agent_manager
        self.bootstrap = bootstrap
        self.registry = registry
        self.event_bus = event_bus
        self.persistence = persistence
        self.restart_events = RestartEventEmitter(event_bus)
        self.lifecycle = RuntimeLifecycle(self)
        self.restart_manager = RestartManager(self)
        self.persistence_runtime = RuntimeContextPersistence(self, persistence)

    def services(self):
        return {
            "kernel": self.kernel,
            "agent_manager": self.agent_manager,
            "bootstrap": self.bootstrap,
            "registry": self.registry,
            "event_bus": self.event_bus,
            "persistence": self.persistence,
        }

    def start(self):
        return self.lifecycle.start()

    def stop(self):
        return self.lifecycle.stop()

    def restart(self):
        return self.restart_manager.restart()

    def history(self):
        return self.persistence_runtime.history()

    def last_recovery(self):
        return self.persistence_runtime.last_recovery()
