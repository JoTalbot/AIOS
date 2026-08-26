from dataclasses import dataclass, field
from typing import Any


@dataclass
class SupervisorState:
    healthy: bool = True
    failures: list[str] = field(default_factory=list)
    recovery_attempts: int = 0


class Supervisor:
    """Coordinates runtime health, recovery decisions and persistence."""

    def __init__(self, recovery=None, persistence=None):
        self.recovery = recovery
        self.persistence = persistence
        self.state = SupervisorState()

    def observe(self, component: str, event: str, payload: Any = None):
        if event == "failure":
            self.state.healthy = False
            self.state.failures.append(component)
            self.state.recovery_attempts += 1
            decision = self._recover(component, payload)
            self._record_recovery(component, decision)
            return decision
        if event == "success":
            self.state.healthy = True
        return self.state

    def _recover(self, component: str, payload: Any = None):
        if self.recovery and hasattr(self.recovery, "evaluate"):
            from execution.recovery import RecoverySignal
            signal = RecoverySignal(
                component=component,
                error=str(payload),
                attempts=self.state.recovery_attempts,
            )
            return self.recovery.evaluate(signal)
        if self.recovery and hasattr(self.recovery, "recover"):
            return self.recovery.recover(component, payload)
        return None

    def _record_recovery(self, component: str, decision: Any):
        if not self.persistence:
            return
        record = {"type": "recovery_decision", "component": component, "decision": decision}
        if hasattr(self.persistence, "record_recovery"):
            self.persistence.record_recovery(record)
        elif hasattr(self.persistence, "record"):
            self.persistence.record(record)
