"""Startup recovery for restart-safe AIOS executions."""

from typing import Any, Optional

from .execution_store import ExecutionState, ExecutionStore


class RecoveryManager:
    """Discover resumable executions and hand them back to the runtime."""

    def __init__(self, store: ExecutionStore):
        self.store = store

    def pending(self):
        return self.store.resumable()

    async def recover(self, loop, agent: Any, context: Optional[dict] = None):
        recovered = []
        for state in self.pending():
            result = await loop.run(
                state.goal,
                agent,
                context=context,
                execution_context=None,
            )
            recovered.append((state.execution_id, result))
        return recovered

    def mark_failed(self, state: ExecutionState, error: BaseException):
        state.status = "failed"
        state.error = str(error)
        return self.store.save(state)
