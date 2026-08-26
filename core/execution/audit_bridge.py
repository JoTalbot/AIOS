"""Bridge execution lifecycle events into the audit layer."""

from typing import Any


class AuditBridge:
    """Small adapter used by lifecycle code to emit audit events."""

    def __init__(self, audit: Any):
        self.audit = audit

    def emit(self, event: str, context: Any = None, **metadata: Any) -> Any:
        payload = {
            "event": event,
            "context": context,
            "metadata": metadata,
        }

        if hasattr(self.audit, "record"):
            return self.audit.record(payload)

        if hasattr(self.audit, "emit"):
            return self.audit.emit(payload)

        return payload
