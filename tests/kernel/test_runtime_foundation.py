from __future__ import annotations

import pytest

from aios_core.runtime import AgentBudget, AgentState, HeartbeatManager, LifecycleManager


def test_lifecycle_requires_ordered_transitions() -> None:
    lifecycle = LifecycleManager()

    assert lifecycle.register("agent-1") is AgentState.CREATED
    assert lifecycle.ready("agent-1") is AgentState.READY
    assert lifecycle.start("agent-1") is AgentState.RUNNING
    assert lifecycle.stop("agent-1") is AgentState.STOPPED

    with pytest.raises(RuntimeError, match="cannot fail"):
        lifecycle.fail("agent-1")


def test_lifecycle_rejects_unknown_or_invalid_start() -> None:
    lifecycle = LifecycleManager()

    with pytest.raises(KeyError, match="unknown agent"):
        lifecycle.start("missing")

    lifecycle.register("agent-1")
    with pytest.raises(RuntimeError, match="expected ready"):
        lifecycle.start("agent-1")


def test_heartbeat_expires_using_monotonic_clock() -> None:
    now = [100.0]
    heartbeat = HeartbeatManager(timeout_seconds=5, clock=lambda: now[0])

    heartbeat.ping("agent-1")
    now[0] = 105.0
    assert heartbeat.alive("agent-1") is True
    now[0] = 105.01
    assert heartbeat.alive("agent-1") is False
    assert heartbeat.alive("missing") is False


def test_budget_rejects_action_after_limit() -> None:
    budget = AgentBudget(max_actions=1)

    budget.consume()

    assert budget.actions_remaining == 0
    assert budget.can_execute() is False
    with pytest.raises(RuntimeError, match="budget exhausted"):
        budget.consume()
