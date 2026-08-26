from execution.events import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    EXECUTION_RECOVERY,
    EXECUTION_STARTED,
    TERMINAL_EXECUTION_EVENTS,
    build_event,
)


def test_execution_event_vocabulary_is_complete_and_terminal_events_are_explicit():
    assert EXECUTION_STARTED == "execution.started"
    assert EXECUTION_COMPLETED == "execution.completed"
    assert EXECUTION_RECOVERY == "execution.recovery"
    assert EXECUTION_FAILED == "execution.failed"
    assert TERMINAL_EXECUTION_EVENTS == frozenset({EXECUTION_COMPLETED, EXECUTION_FAILED})


def test_build_event_preserves_task_identity_and_payload():
    assert build_event(EXECUTION_STARTED, "task-1", attempt=1) == {
        "type": "execution.started",
        "task_id": "task-1",
        "attempt": 1,
    }
