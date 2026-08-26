"""Public execution-layer contracts for AIOS vNext."""

from .checkpoint import Checkpoint, CheckpointStore
from .checkpoint_adapter import PersistenceCheckpointStore
from .coordinator import ExecutionCoordinator
from .event_sink import ExecutionEventSink
from .events import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    EXECUTION_RECOVERY,
    EXECUTION_STARTED,
    TERMINAL_EXECUTION_EVENTS,
    build_event,
)
from .lifecycle import ExecutionAttempt, ExecutionLifecycle
from .result import ExecutionResult

__all__ = [
    "Checkpoint",
    "CheckpointStore",
    "PersistenceCheckpointStore",
    "ExecutionCoordinator",
    "ExecutionEventSink",
    "ExecutionAttempt",
    "ExecutionLifecycle",
    "ExecutionResult",
    "EXECUTION_STARTED",
    "EXECUTION_COMPLETED",
    "EXECUTION_RECOVERY",
    "EXECUTION_FAILED",
    "TERMINAL_EXECUTION_EVENTS",
    "build_event",
]
