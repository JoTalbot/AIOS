"""Recovery-aware execution lifecycle integration."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class RecoveryOutcome:
    recovered: bool
    action: str
    value: Any = None


class RecoveryLifecycle:
    """Connects execution failures with recovery decisions."""

    def __init__(self, executor: Callable[..., Any], recovery):
        self.executor = executor
        self.recovery = recovery

    async def run(self, context: Any) -> Any:
        try:
            return await self.executor(context)
        except Exception as exc:
            decision = await self.recovery.handle(exc, context)
            return RecoveryOutcome(
                recovered=True,
                action=getattr(decision, "action", "retry"),
                value=decision,
            )
