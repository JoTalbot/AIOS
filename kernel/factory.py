"""Factory for constructing the new AIOS kernel stack."""

from .runtime_context import RuntimeContext
from .runtime_persistence_facade import RuntimePersistenceFacade

try:
    from supervision.supervisor import Supervisor
except ImportError:
    Supervisor = None

try:
    from execution.recovery import RecoveryEngine
except ImportError:
    RecoveryEngine = None


class KernelFactory:
    """Build core services through the dependency container and registry."""

    def __init__(self, container, registry=None):
        self.container = container
        self.registry = registry

    def register_services(self):
        if not self.registry:
            return
        for name in self.container.list_services():
            self.registry.register(name, self.container.resolve(name))

    def wire_registry(self):
        if self.registry and hasattr(self.registry, "wire_container"):
            self.registry.wire_container(self.container)

    def create_runtime(self):
        self.register_services()
        self.wire_registry()

        bootstrap = self.container.resolve("bootstrap")
        event_bus = self.container.resolve("event_bus") if self.container.has("event_bus") else None
        context = RuntimeContext(
            kernel=self.container.resolve("kernel"),
            agent_manager=self.container.resolve("agent_manager"),
            bootstrap=bootstrap,
            registry=self.registry,
            event_bus=event_bus,
            persistence=RuntimePersistenceFacade(),
        )

        persistence = None
        if self.container.has("persistence"):
            persistence = self.container.resolve("persistence")
        elif self.container.has("persistence_store"):
            persistence = self.container.resolve("persistence_store")
        if persistence:
            context.persistence_runtime.attach(RuntimePersistenceFacade(persistence))

        if Supervisor:
            recovery = RecoveryEngine() if RecoveryEngine else None
            context.supervisor = Supervisor(recovery=recovery, persistence=context.persistence)
        return context

    def create_kernel(self):
        return self.create_runtime().kernel
