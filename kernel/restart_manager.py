"""Runtime restart orchestration for AIOS kernel stack."""

import inspect

from .restart_events import RestartEventEmitter


class RestartManager:
    """Coordinates restart operations, including vNext scheduler recovery."""

    def __init__(self, context, event_emitter=None):
        self.context = context
        self.events = event_emitter or RestartEventEmitter(
            getattr(context, "event_bus", None)
        )

    def restart(self):
        self.events.started({"source": "restart_manager"})
        orchestrator = getattr(self.context, "orchestrator", None)
        if orchestrator is not None:
            self._call(orchestrator, "stop")
        self.context.stop()
        self.context.start()
        if orchestrator is not None:
            self._call(orchestrator, "start")
        self.events.recovered({"source": "restart_manager", "orchestrator": orchestrator is not None})
        self.events.completed({"source": "restart_manager"})
        return self.context

    @staticmethod
    def _call(target, method_name):
        method = getattr(target, method_name, None)
        if method is None:
            return None
        result = method()
        # RuntimeContext.restart() is synchronous; execute lifecycle coroutines only
        # when a loop is not already running. Async callers should use orchestrator
        # lifecycle directly to avoid nesting event loops.
        if inspect.isawaitable(result):
            try:
                import asyncio
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(result)
            return result
        return result
