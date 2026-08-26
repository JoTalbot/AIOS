"""Audit-aware execution lifecycle helpers."""

from typing import Any


class AuditedExecutionLifecycle:
    """Connects execution lifecycle events with an audit sink."""

    def __init__(self, lifecycle: Any, audit_bridge: Any):
        self.lifecycle = lifecycle
        self.audit_bridge = audit_bridge

    async def execute(self, context: Any):
        self.audit_bridge.emit("execution.started", {"context": context})
        try:
            result = await self.lifecycle.execute(context)
            self.audit_bridge.emit(
                "execution.completed",
                {"result": result},
            )
            return result
        except Exception as exc:
            self.audit_bridge.emit(
                "execution.failed",
                {"error": exc},
            )
            raise
