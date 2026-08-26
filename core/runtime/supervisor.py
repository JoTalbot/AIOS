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

    def _emit(self, name, **metadata):
        if self.hooks:
            self.hooks.emit(HookEvent(name=name, metadata=metadata))

    def start(self):
        restored = self.state_store.load(self.agent_id)
        self.running = True
        self._emit("runtime.start", running=self.running, restored_state=restored)
        return restored

    def stop(self, state=None):
        if state is not None:
            self.state_store.save(self.agent_id, state)
        self.running = False
        self._emit("runtime.stop", running=self.running)

    def fail(self, error):
        self._emit("runtime.error", error=str(error))
