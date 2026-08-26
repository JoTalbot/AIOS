"""Recovery bridge for execution lifecycle integration.

Connects recovery decisions with execution event flow without coupling
runtime components to a concrete recovery implementation.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class RecoveryEvent:
    event: str
    payload: dict[str, Any]


class RecoveryBridge:
    """Adapter between recovery engine and execution lifecycle."""

    def __init__(self, engine: Any, emit: Callable[[RecoveryEvent], None] | None = None):
        self.engine = engine
        self.emit = emit

    def evaluate(self, signal: Any) -> Any:
        decision = self.engine.evaluate(signal)
        if self.emit:
            self.emit(
                RecoveryEvent(
                    event=f"recovery.{decision.action.value}",
                    payload={
                        "reason": decision.reason,
                        "confidence": decision.confidence,
                    },
                )
            )
        return decision
