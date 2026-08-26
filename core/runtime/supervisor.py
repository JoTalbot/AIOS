"""Runtime supervisor foundation."""

from .agent_hooks import HookEvent
from .state_store import StateStore


class RuntimeSupervisor:
    def __init__(self, runtime=None, hooks=None, state_store=None, agent_id="default"):
        self.runtime = runtime
        self.hooks = hooks
        self.state_store = state_store or StateStore()
        self.agent_id = agent_id
        self.running = False
        self.last_checkpoint = None

    def _emit(self, name, **metadata):
        if self.hooks:
            self.hooks.emit(HookEvent(name=name, metadata=metadata))

    async def _emit_async(self, name, **metadata):
        if self.hooks and hasattr(self.hooks, "emit_async"):
            await self.hooks.emit_async(HookEvent(name=name, metadata=metadata))

    def checkpoint(self, state):
        self.last_checkpoint = dict(state) if isinstance(state, dict) else state
        self.state_store.save(self.agent_id, self.last_checkpoint)
        self._emit("state.checkpoint", agent_id=self.agent_id)

    def start(self):
        restored = self.state_store.load(self.agent_id)
        self.running = True
        self._emit("runtime.start", running=self.running, restored_state=restored)
        if restored is not None:
            self._emit("state.restored", agent_id=self.agent_id, state=restored)
        return restored

    async def start_async(self):
        restored = self.state_store.load(self.agent_id)
        self.running = True
        await self._emit_async("runtime.start", running=self.running, restored_state=restored)
        if restored is not None:
            await self._emit_async("state.restored", agent_id=self.agent_id, state=restored)
        return restored

    def stop(self, state=None):
        if state is not None:
            self.state_store.save(self.agent_id, state)
        self.running = False
        self._emit("runtime.stop", running=self.running)

    async def stop_async(self, state=None):
        if state is not None:
            self.state_store.save(self.agent_id, state)
        self.running = False
        await self._emit_async("runtime.stop", running=self.running)

    def fail(self, error):
        self.running = False
        restored = self.state_store.load(self.agent_id)
        self._emit("runtime.error", error=str(error), recovery_state=restored)
        if restored is not None:
            self._emit("state.rollback", agent_id=self.agent_id, state=restored)
        return restored
