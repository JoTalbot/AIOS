"""Runtime context for the AIOS kernel stack."""

import asyncio
import inspect

from .runtime_lifecycle import RuntimeLifecycle
from .restart_manager import RestartManager
from .restart_events import RestartEventEmitter
from .runtime_context_persistence import RuntimeContextPersistence


class RuntimeContext:
    """Single object carrying wired kernel services and recovery lifecycle."""

    def __init__(self, kernel=None, agent_manager=None, bootstrap=None, registry=None, event_bus=None, persistence=None, orchestrator=None, scheduler=None, checkpoint_store=None, checkpoint_recovery=None):
        self.kernel = kernel
        self.agent_manager = agent_manager
        self.bootstrap = bootstrap
        self.registry = registry
        self.event_bus = event_bus
        self.persistence = persistence
        self.orchestrator = orchestrator
        self.scheduler = scheduler
        self.checkpoint_store = checkpoint_store
        self.supervisor = None
        self._checkpoint_recovery = checkpoint_recovery
        self._recovery_initialized = False
        self._recovery_lock = asyncio.Lock()
        self._restart_lock = asyncio.Lock()
        self.restart_events = RestartEventEmitter(event_bus)
        self.lifecycle = RuntimeLifecycle(self)
        self.restart_manager = RestartManager(self)
        self.persistence_runtime = RuntimeContextPersistence(self, persistence)

    def services(self):
        return {"kernel": self.kernel, "agent_manager": self.agent_manager, "bootstrap": self.bootstrap, "registry": self.registry, "event_bus": self.event_bus, "persistence": self.persistence, "supervisor": self.supervisor, "orchestrator": self.orchestrator, "scheduler": self.scheduler, "checkpoint_store": self.checkpoint_store}

    async def _await_checkpoint_recovery(self):
        if self._recovery_initialized:
            return self._checkpoint_recovery or []
        async with self._recovery_lock:
            if self._recovery_initialized:
                return self._checkpoint_recovery or []
            recovery = self._checkpoint_recovery
            if recovery is not None and inspect.isawaitable(recovery):
                recovery = await recovery
                self._checkpoint_recovery = recovery
            self._recovery_initialized = True
            return recovery or []

    async def recover(self):
        return await self._await_checkpoint_recovery()

    async def start_async(self):
        await self._await_checkpoint_recovery()
        self.lifecycle.start()
        if self.scheduler is not None:
            await self.scheduler.start()
        return self

    async def stop_async(self):
        if self.scheduler is not None:
            await self.scheduler.stop()
        self.lifecycle.stop()
        return self

    async def restart_async(self):
        async with self._restart_lock:
            await self.stop_async()
            await self._await_checkpoint_recovery()
            if self.scheduler is not None:
                self.scheduler._worker_tasks = [w for w in self.scheduler._worker_tasks if not w.done()]
                await self.scheduler.start()
            self.lifecycle.start()
            return self

    async def execute(self, goal, task_id, metadata=None):
        if self.orchestrator is None:
            raise RuntimeError("vNext orchestrator is not configured")
        await self._await_checkpoint_recovery()
        return await self.orchestrator.run(goal, task_id, metadata)

    def start(self):
        if self.supervisor and hasattr(self.supervisor, "observe"):
            self.supervisor.observe("runtime", "success")
        return self.lifecycle.start()

    def stop(self): return self.lifecycle.stop()
    def restart(self): return self.restart_manager.restart()
    def history(self): return self.persistence_runtime.history()
    def last_recovery(self): return self.persistence_runtime.last_recovery()
