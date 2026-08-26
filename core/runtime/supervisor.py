"""Runtime supervisor foundation."""

from .agent_hooks import HookEvent


class RuntimeSupervisor:
    def __init__(self, runtime=None, hooks=None):
        self.runtime = runtime
        self.hooks = hooks
        self.running = False

    def _emit(self, name, **metadata):
        if self.hooks:
            self.hooks.emit(HookEvent(name=name, metadata=metadata))

    def start(self):
        self.running = True
        self._emit("runtime.start", running=self.running)

    def stop(self):
        self.running = False
        self._emit("runtime.stop", running=self.running)

    def fail(self, error):
        self._emit("runtime.error", error=str(error))
