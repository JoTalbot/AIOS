"""Autonomous recovery primitives for AIOS execution flows.

Provides deterministic recovery decisions that can be consumed by
runtime coordinators and multi-agent consensus layers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List


class RecoveryAction(str, Enum):
    RETRY = "retry"
    RESTORE = "restore"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class RecoverySignal:
    component: str
    error: str
    attempts: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class RecoveryDecision:
    action: RecoveryAction
    reason: str
    confidence: float


@dataclass
class RecoveryResult:
    recovered: bool
    value: Any = None


class RecoveryHandler:
    """Optional recovery callback after execution failure."""

    def __init__(self, handler: Callable[[Exception, Any], Any] | None = None):
        self.handler = handler

    async def recover(self, error: Exception, context: Any) -> RecoveryResult:
        if self.handler is None:
            return RecoveryResult(recovered=False)

        return RecoveryResult(
            recovered=True,
            value=self.handler(error, context),
        )


class RecoveryEngine:
    """Small deterministic recovery brain for execution orchestration."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.history: List[RecoverySignal] = []

    def evaluate(self, signal: RecoverySignal) -> RecoveryDecision:
        self.history.append(signal)

        if signal.attempts < self.max_retries:
            return RecoveryDecision(
                RecoveryAction.RETRY,
                "Transient failure budget available",
                0.8,
            )

        if signal.metadata.get("checkpoint") == "available":
            return RecoveryDecision(
                RecoveryAction.RESTORE,
                "Checkpoint detected after retry exhaustion",
                0.9,
            )

        if signal.metadata.get("consensus") == "required":
            return RecoveryDecision(
                RecoveryAction.ESCALATE,
                "Multi-agent consensus required",
                0.7,
            )

        return RecoveryDecision(
            RecoveryAction.ABORT,
            "No safe recovery strategy found",
            0.6,
        )
