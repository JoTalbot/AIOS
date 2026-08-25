"""Тесты state machine OpenHands-контура (без моков — чистые переходы и гейты)."""

import pytest

from aios_core.openhands import (
    Gate,
    TaskExtras,
    TransitionError,
    allowed_transitions,
    can_transition,
    transition,
)
from aios_core.openhands.state_machine import OHStatus
from aios_core.orchestrator import TaskStatus


@pytest.fixture
def extras() -> TaskExtras:
    return TaskExtras(task_id="t-1", required_gates=frozenset({Gate.TESTS, Gate.REVIEW}))


class TestHappyPath:
    def test_full_chain(self, extras):
        s = transition(TaskStatus.PENDING, TaskStatus.PLANNING, extras)
        s = transition(s, OHStatus.READY, extras)
        s = transition(s, TaskStatus.RUNNING, extras)
        s = transition(s, OHStatus.TESTING, extras)
        s = transition(s, OHStatus.REVIEW, extras)
        assert extras.passed_gates >= {Gate.TESTS}
        s = transition(s, OHStatus.SECURITY_REVIEW, extras)
        assert extras.passed_gates >= {Gate.TESTS, Gate.REVIEW}
        s = transition(s, OHStatus.QA, extras)
        s = transition(s, TaskStatus.COMPLETED, extras)
        assert s == TaskStatus.COMPLETED
        assert extras.gates_satisfied()

    def test_completed_is_terminal(self, extras):
        assert allowed_transitions(TaskStatus.COMPLETED) == frozenset()

    def test_cancelled_is_terminal(self, extras):
        assert allowed_transitions(TaskStatus.CANCELLED) == frozenset()

    def test_str_and_enum_inputs_equivalent(self, extras):
        assert can_transition("pending", "planning")
        assert can_transition(TaskStatus.PENDING, TaskStatus.PLANNING)
        assert transition("pending", "planning", extras) == "planning"


class TestGates:
    def test_completed_requires_all_gates(self, extras):
        with pytest.raises(TransitionError, match="не пройдены гейты"):
            transition(OHStatus.QA, TaskStatus.COMPLETED, extras)

    def test_completed_allowed_without_required_gates(self):
        light = TaskExtras(task_id="t-2", required_gates=frozenset())
        assert transition(OHStatus.QA, TaskStatus.COMPLETED, light) == "completed"

    def test_gate_passed_only_on_success_exit(self, extras):
        transition(OHStatus.TESTING, TaskStatus.FAILED, extras)
        assert Gate.TESTS not in extras.passed_gates

    def test_gate_not_passed_on_block(self, extras):
        transition(OHStatus.REVIEW, OHStatus.BLOCKED, extras)
        assert Gate.REVIEW not in extras.passed_gates


class TestIllegalTransitions:
    @pytest.mark.parametrize(
        ("src", "dst"),
        [
            ("pending", "running"),
            ("pending", "completed"),
            ("running", "completed"),
            ("running", "review"),
            ("testing", "completed"),
            ("testing", "blocked"),
            ("qa", "review"),
            ("failed", "running"),
            ("blocked", "running"),
        ],
    )
    def test_rejected(self, extras, src, dst):
        assert not can_transition(src, dst)
        with pytest.raises(TransitionError):
            transition(src, dst, extras)


class TestRetryPolicy:
    def test_failed_retry_consumes_attempt(self, extras):
        transition(TaskStatus.FAILED, TaskStatus.PLANNING, extras)
        assert extras.retry_count == 1

    def test_blocked_retry_consumes_attempt(self, extras):
        transition(OHStatus.BLOCKED, TaskStatus.PLANNING, extras)
        assert extras.retry_count == 1

    def test_retry_limit(self, extras):
        for _ in range(extras.max_retries):
            transition(TaskStatus.FAILED, TaskStatus.PLANNING, extras)
        assert not extras.can_retry()
        with pytest.raises(TransitionError, match="лимит попыток"):
            transition(TaskStatus.FAILED, TaskStatus.PLANNING, extras)

    def test_cancel_always_allowed_after_limit(self, extras):
        for _ in range(extras.max_retries):
            transition(TaskStatus.FAILED, TaskStatus.PLANNING, extras)
        assert transition(TaskStatus.FAILED, TaskStatus.CANCELLED, extras) == "cancelled"
