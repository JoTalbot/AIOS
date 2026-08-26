"""Factory for constructing the new AIOS kernel stack."""

from .runtime_context import RuntimeContext
from .runtime_persistence_facade import RuntimePersistenceFacade
from .checkpoint_recovery import CheckpointRecovery
from execution.checkpoint_adapter import PersistenceCheckpointStore
from runtime.vnext_orchestrator import VNextOrchestrator

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

    def _build_orchestrator(self, context):
        required = ("planner", "scheduler", "agent")
        if not all(self.container.has(name) for name in required):
            return None
        execution = self.container.resolve("execution") if self.container.has("execution") else None
        reflection = self.container.resolve("reflection") if self.container.has("reflection") else None
        return VNextOrchestrator(
            self.container.resolve("planner"), self.container.resolve("scheduler"),
            self.container.resolve("agent"), reflection=reflection, execution=execution,
        )

    def create_runtime(self):
        self.register_services()
        self.wire_registry()
        bootstrap = self.container.resolve("bootstrap")
        event_bus = self.container.resolve("event_bus") if self.container.has("event_bus") else None
        kernel = self.container.resolve("kernel")
        context = RuntimeContext(
            kernel=kernel, agent_manager=self.container.resolve("agent_manager"),
            bootstrap=bootstrap, registry=self.registry, event_bus=event_bus,
            persistence=RuntimePersistenceFacade(),
        )
        persistence = None
        if self.container.has("persistence"):
            persistence = self.container.resolve("persistence")
        elif self.container.has("persistence_store"):
            persistence = self.container.resolve("persistence_store")
        if persistence:
            facade = RuntimePersistenceFacade(persistence)
            context.persistence_runtime.attach(facade)
            context.persistence = facade
            if self.container.has("scheduler"):
                scheduler = self.container.resolve("scheduler")
                checkpoint_store = PersistenceCheckpointStore(facade)
                scheduler.checkpoint_store = checkpoint_store
                CheckpointRecovery(checkpoint_store).restore(scheduler)
        if Supervisor:
            recovery = RecoveryEngine() if RecoveryEngine else None
            context.supervisor = Supervisor(recovery=recovery, persistence=context.persistence)
        context.orchestrator = self._build_orchestrator(context)
        if context.orchestrator is not None and hasattr(kernel, "attach_orchestrator"):
            kernel.attach_orchestrator(context.orchestrator)
        return context

    def create_kernel(self):
        return self.create_runtime().kernel
