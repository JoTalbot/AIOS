"""Тесты моделей OpenHands-контура: профили, гейты, retry-счётчик."""

from aios_core.openhands import (
    MVP_ROLES,
    AgentPermissions,
    AgentProfile,
    AgentRole,
    FailureReport,
    Gate,
    TaskExtras,
)
from aios_core.openhands.models import MAX_RETRIES


class TestRoles:
    def test_mvp_roles(self):
        assert set(MVP_ROLES) == {
            AgentRole.ORCHESTRATOR,
            AgentRole.ARCHITECT,
            AgentRole.CODER,
            AgentRole.TESTER,
            AgentRole.REVIEWER,
        }

    def test_future_roles_declared(self):
        for role in ("security", "qa", "devops", "android", "ml", "research", "documentation"):
            assert AgentRole(role) is not None


class TestProfile:
    def test_defaults_deny_writes(self):
        perms = AgentPermissions()
        assert perms.allowed_paths == ()
        assert perms.secret_allowlist == ()

    def test_profile_default_retry(self):
        profile = AgentProfile(role=AgentRole.CODER, permissions=AgentPermissions())
        assert profile.max_retries == MAX_RETRIES == 3


class TestTaskExtras:
    def test_default_required_gates(self):
        extras = TaskExtras(task_id="t")
        assert extras.required_gates == frozenset({Gate.TESTS, Gate.REVIEW})
        assert not extras.gates_satisfied()
        assert extras.missing_gates() == frozenset({Gate.TESTS, Gate.REVIEW})

    def test_gates_progress(self):
        extras = TaskExtras(task_id="t")
        extras.passed_gates |= {Gate.TESTS}
        assert extras.missing_gates() == frozenset({Gate.REVIEW})
        extras.passed_gates |= {Gate.REVIEW}
        assert extras.gates_satisfied()

    def test_mark_gate_passed_accepts_only_required_gates(self):
        extras = TaskExtras(task_id="t", required_gates=frozenset({Gate.TESTS}))
        extras.mark_gate_passed(Gate.TESTS)
        assert extras.passed_gates == frozenset({Gate.TESTS})
        extras.mark_gate_passed(Gate.REVIEW)
        assert extras.passed_gates == frozenset({Gate.TESTS})

    def test_retry_counter(self):
        extras = TaskExtras(task_id="t", max_retries=2)
        assert extras.can_retry()
        assert extras.register_retry() == 1
        assert extras.register_retry() == 2
        assert not extras.can_retry()


class TestFailureReport:
    def test_minimal(self):
        report = FailureReport(task_id="t", reason="tests failed", attempts=3)
        assert report.attempts == 3
        assert report.last_error is None
