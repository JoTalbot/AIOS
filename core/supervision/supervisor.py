from dataclasses import dataclass, field
from typing import Any


@dataclass
class SupervisorState:
    healthy: bool = True
    failures: list[str] = field(default_factory=list)


class Supervisor:
    """Coordinates runtime health and recovery decisions."""

    def __init__(self, recovery=None):
        self.recovery = recovery
        self.state = SupervisorState()

    def observe(self, component: str, event: str, payload: Any = None):
        if event == "failure":
            self.state.healthy = False
            self.state.failures.append(component)
            self._recover(component, payload)
        return self.state

    def _recover(self, component: str, payload: Any = None):
        if self.recovery and hasattr(self.recovery, "recover"):
            return self.recovery.recover(component, payload)
        return None
