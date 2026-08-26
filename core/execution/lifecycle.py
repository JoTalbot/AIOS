"""Execution lifecycle helpers."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class ExecutionAttempt:
    attempt: int
    error: Exception | None = None


class ExecutionLifecycle:
    """Adds retry and recovery hooks around execution."""

    def __init__(
        self,
        executor: Callable[[Any], Awaitable[Any]],
        retries: int = 0,
        recovery: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        self.executor = executor
        self.retries = retries
        self.recovery = recovery

    async def run(self, context: Any) -> Any:
        last_error = None

        for _ in range(self.retries + 1):
            try:
                return await self.executor(context)
            except Exception as exc:
                last_error = exc
                if self.recovery:
                    await self.recovery(exc)

        raise last_error
