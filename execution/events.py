"""Canonical execution event names and event builder."""

EXECUTION_STARTED = "execution.started"
EXECUTION_COMPLETED = "execution.completed"
EXECUTION_RECOVERY = "execution.recovery"
EXECUTION_FAILED = "execution.failed"


TERMINAL_EXECUTION_EVENTS = frozenset({EXECUTION_COMPLETED, EXECUTION_FAILED})


def build_event(event_type, task_id, **data):
    return {"type": event_type, "task_id": task_id, **data}
