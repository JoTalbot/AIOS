"""Operator-facing service for persistent AIOS recovery queues."""

from dataclasses import asdict
from typing import Optional

from .recovery_queue import RecoveryQueue, RecoveryQueueItem


class RecoveryOperatorService:
    """Thin application service; transport layers can expose these methods over HTTP/CLI."""

    def __init__(self, queue: Optional[RecoveryQueue] = None):
        self.queue = queue or RecoveryQueue()

    def list(self, action: Optional[str] = None):
        return [asdict(item) for item in self.queue.items(action=action, unresolved_only=True)]

    def resolve(self, execution_id: str, action: str):
        items = self.queue.items(action=action, unresolved_only=True)
        target = next((item for item in items if item.execution_id == execution_id), None)
        if target is None:
            return False
        self.queue.enqueue(RecoveryQueueItem(target.execution_id, target.action, target.reason, target.attempt, target.correlation_id, target.created_at, resolved=True))
        return True

    def resolve_item(self, execution_id: str, action: str):
        return self.resolve(execution_id, action)
