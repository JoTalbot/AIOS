"""Shared execution status vocabulary."""

EXECUTION_COMPLETED_STATUS = "completed"
EXECUTION_FAILED_STATUS = "failed"

TERMINAL_EXECUTION_STATUSES = frozenset({EXECUTION_COMPLETED_STATUS, EXECUTION_FAILED_STATUS})


def is_terminal_status(status: str) -> bool:
    return status in TERMINAL_EXECUTION_STATUSES
