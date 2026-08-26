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
        if execution is not None and context.persistence is not None and hasattr(execution, "persistence"):
            execution.persistence = context.persistence
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
        persistence = None
        if self.container.has("persistence"):
            persistence = self.container.resolve("persistence")
        elif self.container.has("persistence_store"):
            persistence = self.container.resolve("persistence_store")
        persistence_facade = RuntimePersistenceFacade(persistence) if persistence else RuntimePersistenceFacade()
        scheduler = self.container.resolve("scheduler") if self.container.has("scheduler") else None
        checkpoint_store = None
        recovery = None
        if scheduler is not None and persistence:
            checkpoint_store = PersistenceCheckpointStore(persistence_facade)
            scheduler.checkpoint_store = checkpoint_store
            recovery = CheckpointRecovery(checkpoint_store, persistence_facade)
        context = RuntimeContext(
            kernel=kernel, agent_manager=self.container.resolve("agent_manager"),
            bootstrap=bootstrap, registry=self.registry, event_bus=event_bus,
            persistence=persistence_facade, scheduler=scheduler,
            checkpoint_store=checkpoint_store, checkpoint_recovery=recovery,
        )
        context.persistence_runtime.attach(persistence_facade)
        if Supervisor:
            recovery_engine = RecoveryEngine() if RecoveryEngine else None
            context.supervisor = Supervisor(recovery=recovery_engine, persistence=context.persistence)
        context.orchestrator = self._build_orchestrator(context)
        if context.orchestrator is not None and hasattr(kernel, "attach_orchestrator"):
            kernel.attach_orchestrator(context.orchestrator)
        return context

    def create_kernel(self):
        return self.create_runtime().kernel
