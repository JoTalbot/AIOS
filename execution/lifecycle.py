"""Execution lifecycle helpers."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .event_sink import ExecutionEventSink
from .events import EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_RECOVERY, build_event


@dataclass
class ExecutionAttempt:
    attempt: int
    error: Exception | None = None


class ExecutionLifecycle:
    """Adds retry, recovery and canonical event hooks around execution."""

    def __init__(
        self,
        executor: Callable[[Any], Awaitable[Any]],
        retries: int = 0,
        recovery: Callable[[Exception], Awaitable[None]] | None = None,
        event_sink: ExecutionEventSink | None = None,
        task_id: str = "unknown",
    ):
        self.executor = executor
        self.retries = retries
        self.recovery = recovery
        self.event_sink = event_sink or ExecutionEventSink()
        self.task_id = task_id

    async def run(self, context: Any) -> Any:
        last_error = None
        for attempt in range(1, self.retries + 2):
            try:
                value = await self.executor(context)
                self.event_sink.emit(build_event(EXECUTION_COMPLETED, self.task_id, attempt=attempt))
                return value
            except Exception as exc:
                last_error = exc
                self.event_sink.emit(build_event(EXECUTION_RECOVERY, self.task_id, attempt=attempt, error=str(exc)))
                if self.recovery:
                    await self.recovery(exc)
        self.event_sink.emit(build_event(EXECUTION_FAILED, self.task_id, attempt=self.retries + 1, error=str(last_error)))
        raise last_error
