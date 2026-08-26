"""Startup orchestration for restart-safe AIOS runtime recovery."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from .execution_store import ExecutionStore
from .recovery_manager import RecoveryManager


@dataclass(frozen=True)
class RecoveryReport:
    discovered: int
    attempted: int
    recovered: int
    failed: int


class RuntimeBootstrap:
    def __init__(self, store: Optional[ExecutionStore] = None, recovery_manager: Optional[RecoveryManager] = None):
        self.store = store or ExecutionStore()
        self.recovery_manager = recovery_manager or RecoveryManager(self.store)

    async def recover_pending(self, resume: Callable[[Any], Awaitable[Any]]) -> RecoveryReport:
        pending = self.store.resumable()
        recovered = failed = 0
        for state in pending:
            try:
                await resume(state)
                recovered += 1
            except Exception:
                failed += 1
        return RecoveryReport(len(pending), len(pending), recovered, failed)
