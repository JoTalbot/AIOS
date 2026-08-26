"""Startup orchestration for restart-safe AIOS runtime recovery."""

import asyncio
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
    def __init__(self, store: Optional[ExecutionStore] = None, recovery_manager: Optional[RecoveryManager] = None, lease_store: Optional[ExecutionLeaseStore] = None, owner_id: str = "aios-runtime", heartbeat_interval: Optional[float] = None):
        self.store = store or ExecutionStore()
        self.recovery_manager = recovery_manager or RecoveryManager(self.store)
        self.lease_store = lease_store or ExecutionLeaseStore()
        self.owner_id = owner_id
        ttl = self.lease_store.ttl_seconds
        self.heartbeat_interval = heartbeat_interval if heartbeat_interval is not None else max(0.1, ttl / 3)

    async def _heartbeat(self, execution_id: str):
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            if self.lease_store.renew(execution_id, self.owner_id) is None:
                raise RuntimeError(f"execution lease lost: {execution_id}")

    async def recover_pending(self, resume: Callable[[Any], Awaitable[Any]]) -> RecoveryReport:
        pending = self.store.resumable()
        recovered = failed = skipped = 0
        for state in pending:
            lease = self.lease_store.acquire(state.execution_id, self.owner_id)
            if lease is None:
                skipped += 1
                continue
            heartbeat = asyncio.create_task(self._heartbeat(state.execution_id))
            try:
                await resume(state)
                recovered += 1
            except Exception as exc:
                failed += 1
                if hasattr(self.recovery_manager, "mark_failed"):
                    self.recovery_manager.mark_failed(state, exc)
            finally:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
                self.lease_store.release(state.execution_id, self.owner_id)
        return RecoveryReport(len(pending), recovered + failed, recovered, failed, skipped)

    async def recover_with_loop(self, loop, agent: Any, context: Optional[dict] = None) -> RecoveryReport:
        return await self.recover_pending(lambda state: loop.resume(state.execution_id, agent, context=context))
