"""Canonical execution event names and event builder."""

EXECUTION_COMPLETED = "execution.completed"
EXECUTION_RECOVERY = "execution.recovery"
EXECUTION_FAILED = "execution.failed"


def build_event(event_type, task_id, **data):
    return {"type": event_type, "task_id": task_id, **data}
