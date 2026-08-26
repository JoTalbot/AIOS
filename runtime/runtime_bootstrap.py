"""Startup orchestration for restart-safe AIOS runtime recovery."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from .execution_lease import ExecutionLeaseStore
from .execution_store import ExecutionStore
from .recovery_manager import RecoveryManager


@dataclass(frozen=True)
class RecoveryReport:
    discovered: int
    attempted: int
    recovered: int
    failed: int
    skipped: int = 0


class RuntimeBootstrap:
    def __init__(self, store: Optional[ExecutionStore] = None, recovery_manager: Optional[RecoveryManager] = None, lease_store: Optional[ExecutionLeaseStore] = None, owner_id: str = "aios-runtime"):
        self.store = store or ExecutionStore()
        self.recovery_manager = recovery_manager or RecoveryManager(self.store)
        self.lease_store = lease_store or ExecutionLeaseStore()
        self.owner_id = owner_id

    async def recover_pending(self, resume: Callable[[Any], Awaitable[Any]]) -> RecoveryReport:
        pending = self.store.resumable()
        recovered = failed = skipped = 0
        for state in pending:
            lease = self.lease_store.acquire(state.execution_id, self.owner_id)
            if lease is None:
                skipped += 1
                continue
            try:
                await resume(state)
                recovered += 1
            except Exception as exc:
                failed += 1
                self.recovery_manager.mark_failed(state, exc)
            finally:
                self.lease_store.release(state.execution_id, self.owner_id)
        return RecoveryReport(len(pending), recovered + failed, recovered, failed, skipped)

    async def recover_with_loop(self, loop, agent: Any, context: Optional[dict] = None) -> RecoveryReport:
        return await self.recover_pending(lambda state: loop.resume(state.execution_id, agent, context=context))
