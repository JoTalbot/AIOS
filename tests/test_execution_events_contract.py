from execution.events import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    EXECUTION_RECOVERY,
    EXECUTION_STARTED,
    TERMINAL_EXECUTION_EVENTS,
    build_event,
)


def test_execution_event_contract_is_canonical():
    assert EXECUTION_STARTED == "execution.started"
    assert EXECUTION_COMPLETED == "execution.completed"
    assert EXECUTION_RECOVERY == "execution.recovery"
    assert EXECUTION_FAILED == "execution.failed"
    assert TERMINAL_EXECUTION_EVENTS == frozenset({EXECUTION_COMPLETED, EXECUTION_FAILED})


def test_build_event_preserves_task_identity_and_metadata():
    event = build_event(EXECUTION_STARTED, "task-42", source="coordinator", attempt=1)
    assert event == {
        "type": EXECUTION_STARTED,
        "task_id": "task-42",
        "source": "coordinator",
        "attempt": 1,
    }
