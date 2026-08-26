"""Unified recovery lifecycle coordination for AIOS.

Connects execution failures with recovery decisions and persistence hooks.
"""

from typing import Any

from .recovery import RecoveryEngine, RecoverySignal


class RecoveryLifecycle:
    """Coordinates failure observation and recovery execution decisions."""

    def __init__(self, engine=None, persistence=None):
        self.engine = engine or RecoveryEngine()
        self.persistence = persistence
        self.history = []

    def handle_failure(self, component: str, error: Exception | str, attempts: int = 0, metadata: dict | None = None):
        signal = RecoverySignal(
            component=component,
            error=str(error),
            attempts=attempts,
            metadata=metadata or {},
        )
        decision = self.engine.evaluate(signal)
        event = {"type": "recovery.lifecycle.decision", "signal": signal, "decision": decision}
        self.history.append(event)
        self._persist(event)
        return decision

    def _persist(self, event: dict[str, Any]):
        if self.persistence is None:
            return
        if hasattr(self.persistence, "record_recovery"):
            self.persistence.record_recovery(event)
        elif hasattr(self.persistence, "record"):
            self.persistence.record(event)
