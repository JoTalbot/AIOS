"""Operator-facing service for persistent AIOS recovery queues."""

from dataclasses import asdict
from typing import Optional

from .recovery_queue import RecoveryQueue


class RecoveryOperatorService:
    """Thin application service; transport layers can expose these methods over HTTP/CLI."""

    def __init__(self, queue: Optional[RecoveryQueue] = None):
        self.queue = queue or RecoveryQueue()

    def list(self, action: Optional[str] = None):
        return [asdict(item) for item in self.queue.items(action=action, unresolved_only=True)]

    def resolve(self, execution_id: str, action: str):
        return self.queue.resolve(execution_id, action)

    def resolve_item(self, execution_id: str, action: str):
        return self.resolve(execution_id, action)
