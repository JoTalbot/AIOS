"""Integration tests for AIOS runtime lifecycle."""

from core.runtime.state_machine import LifecycleState, LifecycleStateMachine


def test_lifecycle_allows_planning_to_running():
    machine = LifecycleStateMachine()

    assert machine.can_transition(
        LifecycleState.CREATED,
        LifecycleState.PLANNED,
    )

    assert machine.can_transition(
        LifecycleState.PLANNED,
        LifecycleState.RUNNING,
    )


def test_recovery_returns_to_running():
    machine = LifecycleStateMachine()

    assert machine.can_transition(
        LifecycleState.RECOVERING,
        LifecycleState.RUNNING,
    )


def test_completed_is_terminal():
    machine = LifecycleStateMachine()

    assert not machine.can_transition(
        LifecycleState.COMPLETED,
        LifecycleState.RUNNING,
    )
