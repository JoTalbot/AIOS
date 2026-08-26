"""Operator-facing service for persistent AIOS recovery queues."""

from dataclasses import asdict
from typing import Optional

from .operator_audit import OperatorAuditEvent, OperatorAuditLog
from .recovery_queue import RecoveryQueue


class RecoveryOperatorService:
    """Application service for recovery operations with durable operator auditing."""

    def __init__(self, queue: Optional[RecoveryQueue] = None, audit_log: Optional[OperatorAuditLog] = None):
        self.queue = queue or RecoveryQueue()
        self.audit_log = audit_log or OperatorAuditLog()

    def list(self, action: Optional[str] = None):
        return [asdict(item) for item in self.queue.items(action=action, unresolved_only=True)]

    def audit_events(self):
        return self.audit_log.events()

    def resolve(self, execution_id: str, action: str, *, actor: str = "operator", reason: Optional[str] = None):
        try:
            changed = self.queue.resolve(execution_id, action)
        except Exception as exc:
            self.audit_log.append(OperatorAuditEvent(action, execution_id, actor, "failed", str(exc)))
            raise
        outcome = "resolved" if changed else "not_found"
        self.audit_log.append(OperatorAuditEvent(action, execution_id, actor, outcome, reason))
        if not changed:
            raise KeyError(f"recovery item not found: {execution_id}/{action}")
        return {"execution_id": execution_id, "action": action, "resolved": True}

    def resolve_item(self, execution_id: str, action: str, *, actor: str = "operator", reason: Optional[str] = None):
        return self.resolve(execution_id, action, actor=actor, reason=reason)
