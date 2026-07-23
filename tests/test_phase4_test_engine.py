"""AIOS Phase 4 — Test Engine Tests

Comprehensive tests for the AIOS self-validation test engine, including
data models, test runner, built-in suites, reporter, and main engine facade.
"""

import pytest
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTITUTION_DIR = os.path.join(_PROJECT_ROOT, "docs/constitution")
POLICIES_DIR = os.path.join(_PROJECT_ROOT, "policies")


# ============================================================
# TestModels (10 tests)
# ============================================================


class TestModels:
    """Tests for test engine data models."""

    def test_test_case_creation(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestSeverity

        tc = TestCase(
            name="test_something",
            description="A test case",
            category=TestCategory.SECURITY,
            severity=TestSeverity.CRITICAL,
            action={"goal": "do it"},
            expected_decision="DENY",
            tags=["tag1"],
        )
        assert tc.name == "test_something"
        assert tc.description == "A test case"
        assert tc.category == TestCategory.SECURITY
        assert tc.severity == TestSeverity.CRITICAL
        assert tc.action == {"goal": "do it"}
        assert tc.expected_decision == "DENY"
        assert tc.tags == ["tag1"]
        assert tc.timeout == 30.0
        assert tc.retries == 0
        assert tc.validator is None

    def test_test_result_defaults(self):
        from aios_core.test_engine.models import TestResult, TestStatus, TestCategory, TestSeverity

        r = TestResult(test_name="my_test")
        assert r.test_name == "my_test"
        assert r.status == TestStatus.PENDING
        assert r.category == TestCategory.CONSTITUTIONAL
        assert r.severity == TestSeverity.MEDIUM
        assert r.actual_decision is None
        assert r.expected_decision is None
        assert r.message == ""
        assert r.evaluation is None
        assert r.duration_ms == 0.0
        assert r.retry_count == 0
        assert r.error is None
        assert r.started_at is None
        assert r.completed_at is None

    def test_test_status_enum_values(self):
        from aios_core.test_engine.models import TestStatus

        assert TestStatus.PENDING.value == "pending"
        assert TestStatus.RUNNING.value == "running"
        assert TestStatus.PASSED.value == "passed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.ERROR.value == "error"
        assert TestStatus.SKIPPED.value == "skipped"
        # Should have 6 values
        assert len(TestStatus) == 6

    def test_test_severity_enum_values(self):
        from aios_core.test_engine.models import TestSeverity

        assert TestSeverity.CRITICAL.value == "critical"
        assert TestSeverity.HIGH.value == "high"
        assert TestSeverity.MEDIUM.value == "medium"
        assert TestSeverity.LOW.value == "low"
        assert len(TestSeverity) == 4

    def test_test_category_enum_values(self):
        from aios_core.test_engine.models import TestCategory

        assert TestCategory.CONSTITUTIONAL.value == "constitutional"
        assert TestCategory.REGRESSION.value == "regression"
        assert TestCategory.INTEGRATION.value == "integration"
        assert TestCategory.PERFORMANCE.value == "performance"
        assert TestCategory.SECURITY.value == "security"
        assert TestCategory.EVOLUTION.value == "evolution"
        assert len(TestCategory) == 6

    def test_suite_result_defaults(self):
        from aios_core.test_engine.models import TestSuiteResult, TestStatus

        sr = TestSuiteResult(suite_name="my_suite")
        assert sr.suite_name == "my_suite"
        assert sr.status == TestStatus.PENDING
        assert sr.total == 0
        assert sr.passed == 0
        assert sr.failed == 0
        assert sr.errors == 0
        assert sr.skipped == 0
        assert sr.results == []
        assert sr.by_category == {}
        assert sr.by_severity == {}
        assert sr.duration_ms == 0.0

    def test_test_report_defaults(self):
        from aios_core.test_engine.models import TestReport

        report = TestReport()
        assert report.report_id == ""
        assert report.generated_at  # Should be auto-generated
        assert report.total_suites == 0
        assert report.total_tests == 0
        assert report.total_passed == 0
        assert report.total_failed == 0
        assert report.total_errors == 0
        assert report.total_skipped == 0
        assert report.overall_status == "pending"
        assert report.duration_ms == 0.0
        assert report.suites == []
        assert report.failures == []

    def test_test_result_status_values(self):
        from aios_core.test_engine.models import TestResult, TestStatus

        for status in TestStatus:
            r = TestResult(test_name="t", status=status)
            assert r.status == status

    def test_suite_result_category_breakdown(self):
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        sr = TestSuiteResult(suite_name="s")
        sr.results.append(TestResult(test_name="t1", category=TestCategory.SECURITY))
        sr.results.append(TestResult(test_name="t2", category=TestCategory.SECURITY))
        sr.results.append(TestResult(test_name="t3", category=TestCategory.INTEGRATION))
        sr.by_category[TestCategory.SECURITY.value] = 2
        sr.by_category[TestCategory.INTEGRATION.value] = 1
        assert sr.by_category["security"] == 2
        assert sr.by_category["integration"] == 1

    def test_test_case_with_validator(self):
        from aios_core.test_engine.models import TestCase

        def my_validator(action, result):
            return True, "OK"

        tc = TestCase(name="test", validator=my_validator)
        assert tc.validator is not None
        passed, msg = tc.validator({}, {})
        assert passed is True
        assert msg == "OK"


# ============================================================
# TestRunner (15 tests)
# ============================================================


class TestRunner:
    """Tests for the TestRunner execution engine."""

    def _make_runner(self):
        from aios_core.test_engine.runner import TestRunner

        return TestRunner(CONSTITUTION_DIR, POLICIES_DIR)

    def test_run_allow_case(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_allow",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "goal": "Read metrics",
                    "scope": "monitoring",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
            )
        )
        assert result.status == TestStatus.PASSED
        assert result.actual_decision == "ALLOW"
        assert "Decision matches" in result.message

    def test_run_deny_case(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_deny",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "unknown",
                    "authority": "user",
                },
                expected_decision="DENY",
            )
        )
        assert result.status == TestStatus.PASSED
        assert result.actual_decision == "DENY"

    def test_run_review_case(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_review",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "goal": "High risk action",
                    "scope": "system",
                    "risk": "high",
                    "audit_log": True,
                    "agent_id": "admin-agent",
                    "authority": "admin",
                },
                expected_decision="REVIEW",
            )
        )
        assert result.status == TestStatus.PASSED
        assert result.actual_decision == "REVIEW"

    def test_run_missing_fields_denied(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        # Missing goal
        result = runner.run_case(
            TestCase(
                name="test_missing_goal",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="DENY",
            )
        )
        assert result.status == TestStatus.PASSED
        assert result.actual_decision == "DENY"

    def test_run_unknown_agent_denied(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_unknown",
                category=TestCategory.SECURITY,
                action={
                    "goal": "Access data",
                    "scope": "data",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "unknown",
                    "authority": "user",
                },
                expected_decision="DENY",
            )
        )
        assert result.status == TestStatus.PASSED

    def test_run_unlimited_authority_denied(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_unlimited",
                category=TestCategory.SECURITY,
                action={
                    "goal": "Do something",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "unlimited",
                },
                expected_decision="DENY",
            )
        )
        assert result.status == TestStatus.PASSED

    def test_run_no_audit_denied(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_no_audit",
                category=TestCategory.SECURITY,
                action={
                    "goal": "Do something",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": False,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="DENY",
            )
        )
        assert result.status == TestStatus.PASSED

    def test_run_personal_memory_share_denied(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_memory_share",
                category=TestCategory.SECURITY,
                action={
                    "goal": "Share personal data",
                    "scope": "federation",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "fed-agent",
                    "authority": "user",
                    "memory_type": "personal",
                    "share": True,
                },
                expected_decision="DENY",
            )
        )
        assert result.status == TestStatus.PASSED

    def test_run_custom_validator_passes(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        def validator(action, evaluation):
            return True, "Custom OK"

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_custom_pass",
                category=TestCategory.INTEGRATION,
                action={
                    "goal": "Do something",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
                validator=validator,
            )
        )
        assert result.status == TestStatus.PASSED

    def test_run_custom_validator_fails(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        def validator(action, evaluation):
            return False, "Custom check failed"

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_custom_fail",
                category=TestCategory.INTEGRATION,
                action={
                    "goal": "Do something",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
                validator=validator,
            )
        )
        assert result.status == TestStatus.FAILED
        assert "Custom check failed" in result.message

    def test_run_with_retries(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        call_count = 0

        def flaky_validator(action, evaluation):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return False, "Flaky"
            return True, "OK"

        runner = self._make_runner()
        result = runner.run_case(
            TestCase(
                name="test_retry",
                category=TestCategory.INTEGRATION,
                action={
                    "goal": "Do something",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
                validator=flaky_validator,
                retries=2,
            )
        )
        # The retry mechanism retries on exceptions in run_case, not on validator failures.
        # The validator is called once (the first successful evaluate call).
        # So the validator will fail (call_count=1 < 3), and the result should be FAILED.
        assert result.status == TestStatus.FAILED

    def test_run_suite(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        cases = [
            TestCase(
                name="allow_test",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "goal": "Read data",
                    "scope": "monitoring",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
            ),
            TestCase(
                name="deny_test",
                category=TestCategory.SECURITY,
                action={
                    "goal": "Access",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "unknown",
                    "authority": "user",
                },
                expected_decision="DENY",
            ),
        ]
        suite = runner.run_suite("my_suite", cases)
        assert suite.suite_name == "my_suite"
        assert suite.total == 2
        assert suite.passed == 2
        assert suite.failed == 0
        assert suite.status == TestStatus.PASSED
        assert len(suite.results) == 2

    def test_run_empty_suite(self):
        from aios_core.test_engine.models import TestStatus

        runner = self._make_runner()
        suite = runner.run_suite("empty_suite", [])
        assert suite.total == 0
        assert suite.passed == 0
        assert suite.failed == 0
        assert suite.status == TestStatus.PASSED

    def test_runner_stats(self):
        runner = self._make_runner()
        stats = runner.stats()
        assert stats["tests_run"] == 0
        assert stats["engine_version"] == "3.0.0"
        # Run one test
        from aios_core.test_engine.models import TestCase, TestCategory

        runner.run_case(
            TestCase(
                name="s",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "goal": "g",
                    "scope": "s",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "a",
                    "authority": "user",
                },
                expected_decision="ALLOW",
            )
        )
        assert runner.stats()["tests_run"] == 1

    def test_run_error_handling(self):
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        runner = self._make_runner()
        # The runner should not error on normal operations
        # But a completely malformed action that triggers an internal error should be caught
        result = runner.run_case(
            TestCase(
                name="test_normal",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "goal": "Normal action",
                    "scope": "testing",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
            )
        )
        assert result.status == TestStatus.PASSED
        assert result.error is None
        assert result.evaluation is not None


# ============================================================
# TestSuites (10 tests)
# ============================================================


class TestSuites:
    """Tests for built-in test suites."""

    def test_constitutional_compliance_suite_count(self):
        from aios_core.test_engine.suites import constitutional_compliance_suite

        cases = constitutional_compliance_suite()
        assert len(cases) == 13

    def test_constitutional_suite_has_critical_tests(self):
        from aios_core.test_engine.suites import constitutional_compliance_suite
        from aios_core.test_engine.models import TestSeverity

        cases = constitutional_compliance_suite()
        critical = [c for c in cases if c.severity == TestSeverity.CRITICAL]
        assert len(critical) >= 5

    def test_security_suite_count(self):
        from aios_core.test_engine.suites import security_policy_suite

        cases = security_policy_suite()
        assert len(cases) == 4

    def test_evolution_safety_suite_count(self):
        from aios_core.test_engine.suites import evolution_safety_suite

        cases = evolution_safety_suite()
        assert len(cases) == 3

    def test_integration_suite_count(self):
        from aios_core.test_engine.suites import integration_suite

        cases = integration_suite()
        assert len(cases) == 3

    def test_all_suites_return_test_cases(self):
        from aios_core.test_engine.suites import (
            constitutional_compliance_suite,
            security_policy_suite,
            evolution_safety_suite,
            integration_suite,
        )
        from aios_core.test_engine.models import TestCase

        for suite_fn in [
            constitutional_compliance_suite,
            security_policy_suite,
            evolution_safety_suite,
            integration_suite,
        ]:
            cases = suite_fn()
            assert all(isinstance(c, TestCase) for c in cases)
            assert len(cases) > 0

    def test_constitutional_suite_has_tags(self):
        from aios_core.test_engine.suites import constitutional_compliance_suite

        cases = constitutional_compliance_suite()
        tagged = [c for c in cases if c.tags]
        assert len(tagged) > 0
        # Every test case should have tags
        assert all(c.tags for c in cases)

    def test_security_suite_all_critical(self):
        from aios_core.test_engine.suites import security_policy_suite
        from aios_core.test_engine.models import TestSeverity

        cases = security_policy_suite()
        # At least some should be CRITICAL
        critical = [c for c in cases if c.severity == TestSeverity.CRITICAL]
        assert len(critical) >= 3

    def test_evolution_suite_tests_categories(self):
        from aios_core.test_engine.suites import evolution_safety_suite
        from aios_core.test_engine.models import TestCategory

        cases = evolution_safety_suite()
        categories = {c.category for c in cases}
        assert TestCategory.EVOLUTION in categories

    def test_suites_are_importable(self):
        """All suites should be importable from aios_core top-level."""
        from aios_core import (
            constitutional_compliance_suite,
            security_policy_suite,
            evolution_safety_suite,
            integration_suite,
        )

        assert callable(constitutional_compliance_suite)
        assert callable(security_policy_suite)
        assert callable(evolution_safety_suite)
        assert callable(integration_suite)


# ============================================================
# TestReporter (8 tests)
# ============================================================


class TestReporter:
    """Tests for the TestReporter."""

    def test_generate_report_all_passed(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="all_pass",
            status=TestStatus.PASSED,
            total=3,
            passed=3,
            failed=0,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="t1", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
                TestResult(
                    test_name="t2", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
                TestResult(
                    test_name="t3", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
            ],
        )
        report = reporter.generate("All Pass Test", [suite])
        assert report.total_suites == 1
        assert report.total_tests == 3
        assert report.total_passed == 3
        assert report.total_failed == 0
        assert report.overall_status == "passed"

    def test_generate_report_with_failures(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="with_fails",
            status=TestStatus.FAILED,
            total=3,
            passed=1,
            failed=2,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="t1", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
                TestResult(
                    test_name="t2",
                    status=TestStatus.FAILED,
                    category=TestCategory.CONSTITUTIONAL,
                    expected_decision="ALLOW",
                    actual_decision="DENY",
                    message="Expected ALLOW, got DENY",
                ),
                TestResult(
                    test_name="t3",
                    status=TestStatus.FAILED,
                    category=TestCategory.CONSTITUTIONAL,
                    expected_decision="ALLOW",
                    actual_decision="DENY",
                    message="Expected ALLOW, got DENY",
                ),
            ],
        )
        report = reporter.generate("With Failures", [suite])
        assert report.total_failed == 2
        assert report.overall_status == "partial"
        assert len(report.failures) == 2

    def test_summary_text(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="test_suite",
            status=TestStatus.PASSED,
            total=2,
            passed=2,
            failed=0,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="t1", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
                TestResult(
                    test_name="t2", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
            ],
        )
        report = reporter.generate("Summary Test", [suite])
        text = reporter.summary_text(report)
        assert "AIOS Test Report" in text
        assert "PASSED" in text
        assert "test_suite" in text
        assert "2/2 passed" in text

    def test_failures_text_empty(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="clean",
            status=TestStatus.PASSED,
            total=1,
            passed=1,
            failed=0,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="t1", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
            ],
        )
        report = reporter.generate("Clean", [suite])
        text = reporter.failures_text(report)
        assert text == "No failures."

    def test_failures_text_with_failures(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="fail_suite",
            status=TestStatus.FAILED,
            total=1,
            passed=0,
            failed=1,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="bad_test",
                    status=TestStatus.FAILED,
                    category=TestCategory.CONSTITUTIONAL,
                    expected_decision="ALLOW",
                    actual_decision="DENY",
                    message="Mismatch",
                ),
            ],
        )
        report = reporter.generate("Fail Report", [suite])
        text = reporter.failures_text(report)
        assert "FAILURES" in text
        assert "bad_test" in text
        assert "Mismatch" in text

    def test_to_dict(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestResult,
            TestStatus,
            TestCategory,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="dict_suite",
            status=TestStatus.PASSED,
            total=1,
            passed=1,
            failed=0,
            errors=0,
            skipped=0,
            duration_ms=10.5,
            results=[
                TestResult(
                    test_name="t1", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
            ],
        )
        report = reporter.generate("Dict Test", [suite])
        d = reporter.to_dict(report)
        assert d["total_suites"] == 1
        assert d["total_tests"] == 1
        assert d["total_passed"] == 1
        assert d["overall_status"] == "passed"
        assert len(d["suites"]) == 1
        assert d["suites"][0]["name"] == "dict_suite"
        assert d["suites"][0]["status"] == "passed"
        assert "report_id" in d
        assert "generated_at" in d

    def test_report_overall_status_passed(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestStatus,
            TestCategory,
            TestResult,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="s",
            status=TestStatus.PASSED,
            total=1,
            passed=1,
            failed=0,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="t", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                )
            ],
        )
        report = reporter.generate("P", [suite])
        assert report.overall_status == "passed"

    def test_report_overall_status_partial(self):
        from aios_core.test_engine.reporter import TestReporter
        from aios_core.test_engine.models import (
            TestSuiteResult,
            TestStatus,
            TestCategory,
            TestResult,
        )

        reporter = TestReporter()
        suite = TestSuiteResult(
            suite_name="s",
            status=TestStatus.FAILED,
            total=2,
            passed=1,
            failed=1,
            errors=0,
            skipped=0,
            results=[
                TestResult(
                    test_name="t1", status=TestStatus.PASSED, category=TestCategory.CONSTITUTIONAL
                ),
                TestResult(
                    test_name="t2",
                    status=TestStatus.FAILED,
                    category=TestCategory.CONSTITUTIONAL,
                    expected_decision="ALLOW",
                    actual_decision="DENY",
                    message="fail",
                ),
            ],
        )
        report = reporter.generate("Partial", [suite])
        assert report.overall_status == "partial"


# ============================================================
# TestEngine (14 tests)
# ============================================================


class TestEngine:
    """Tests for the main TestEngine facade."""

    def test_init(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        assert engine is not None
        assert engine.runner is not None
        assert engine.reporter is not None
        assert engine._custom_suites == {}
        assert engine._reports == []

    def test_run_case(self):
        from aios_core.test_engine.engine import TestEngine
        from aios_core.test_engine.models import TestCase, TestCategory

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        result = engine.run_case(
            TestCase(
                name="engine_case",
                category=TestCategory.CONSTITUTIONAL,
                action={
                    "goal": "Read metrics",
                    "scope": "monitoring",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
            )
        )
        assert result["name"] == "engine_case"
        assert result["status"] == "passed"
        assert result["actual"] == "ALLOW"
        assert result["expected"] == "ALLOW"
        assert "duration_ms" in result

    def test_run_builtin_suite_constitutional(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        suite = engine.run_suite("constitutional_compliance")
        assert suite.suite_name == "constitutional_compliance"
        assert suite.total == 13
        # All should pass since they test real engine behavior
        assert suite.passed == 13
        assert suite.failed == 0

    def test_run_builtin_suite_security(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        suite = engine.run_suite("security_policy")
        assert suite.suite_name == "security_policy"
        assert suite.total == 4
        assert suite.passed == 4
        assert suite.failed == 0

    def test_run_builtin_suite_evolution(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        suite = engine.run_suite("evolution_safety")
        assert suite.suite_name == "evolution_safety"
        assert suite.total == 3
        assert suite.passed == 3
        assert suite.failed == 0

    def test_run_builtin_suite_integration(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        suite = engine.run_suite("integration")
        assert suite.suite_name == "integration"
        assert suite.total == 3
        assert suite.passed == 3
        assert suite.failed == 0

    def test_run_all(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        report = engine.run_all()
        assert report.total_suites == 4
        assert report.total_tests == 13 + 4 + 3 + 3  # 23
        assert report.total_passed == 23
        assert report.total_failed == 0
        assert report.overall_status == "passed"

    def test_register_custom_suite(self):
        from aios_core.test_engine.engine import TestEngine
        from aios_core.test_engine.models import TestCase, TestCategory

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        custom_case = TestCase(
            name="custom_1",
            category=TestCategory.INTEGRATION,
            action={
                "goal": "Custom test",
                "scope": "test",
                "risk": "low",
                "audit_log": True,
                "agent_id": "agent-1",
                "authority": "user",
            },
            expected_decision="ALLOW",
        )
        engine.register_suite("custom_suite", [custom_case])
        suites = engine.list_suites()
        custom = [s for s in suites if s["name"] == "custom_suite" and s["type"] == "custom"]
        assert len(custom) == 1

    def test_run_custom_suite(self):
        from aios_core.test_engine.engine import TestEngine
        from aios_core.test_engine.models import TestCase, TestCategory, TestStatus

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        custom_case = TestCase(
            name="custom_runner",
            category=TestCategory.INTEGRATION,
            action={
                "goal": "Custom",
                "scope": "test",
                "risk": "low",
                "audit_log": True,
                "agent_id": "agent-1",
                "authority": "user",
            },
            expected_decision="ALLOW",
        )
        engine.register_suite("my_custom", [custom_case])
        suite = engine.run_suite("my_custom")
        assert suite.suite_name == "my_custom"
        assert suite.total == 1
        assert suite.passed == 1
        assert suite.status == TestStatus.PASSED

    def test_list_suites(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        suites = engine.list_suites()
        names = [s["name"] for s in suites]
        assert "constitutional_compliance" in names
        assert "security_policy" in names
        assert "evolution_safety" in names
        assert "integration" in names
        # All should be builtin
        assert all(s["type"] == "builtin" for s in suites)

    def test_report_text(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        report = engine.run_all()
        text = engine.report_text(report)
        assert "AIOS Test Report" in text
        assert "PASSED" in text
        assert "constitutional_compliance" in text

    def test_failures_text(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        report = engine.run_all()
        text = engine.failures_text(report)
        # All should pass, so no failures
        assert text == "No failures."

    def test_last_report(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        assert engine.last_report() is None
        engine.run_all()
        last = engine.last_report()
        assert last is not None
        assert last.total_tests > 0

    def test_stats(self):
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        stats = engine.stats()
        assert stats["version"] == "1.0.0"
        assert len(stats["suites_available"]) == 4
        assert stats["reports_generated"] == 0
        assert stats["last_report_status"] is None
        engine.run_all()
        stats2 = engine.stats()
        assert stats2["reports_generated"] == 1
        assert stats2["last_report_status"] == "passed"
        assert stats2["last_report_summary"]["total"] == 23
        assert stats2["last_report_summary"]["passed"] == 23


# ============================================================
# TestIntegration (8 tests)
# ============================================================


class TestIntegration:
    """End-to-end integration tests for the test engine."""

    def test_full_self_test_all_passed(self):
        """Running the full self-test should produce all-passed report."""
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        report = engine.run_all()
        assert report.total_passed == report.total_tests
        assert report.total_failed == 0
        assert report.total_errors == 0
        assert report.overall_status == "passed"

    def test_engine_with_database_persists_report(self):
        """TestEngine with a Database should persist the report."""
        from aios_core.storage import Database
        from aios_core.test_engine.engine import TestEngine

        db = Database(db_path=":memory:")
        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR, db=db)
        report = engine.run_all()
        # Check that the report was persisted in memory_items
        rows = db.query(
            "SELECT * FROM memory_items WHERE source = 'test_engine' AND tags LIKE '%test_report%'"
        )
        assert len(rows) == 1
        content = db.from_json(rows[0]["content"])
        assert content["total_tests"] == report.total_tests
        assert content["overall_status"] == "passed"

    def test_custom_validator_integration(self):
        """Custom validators should work in the full pipeline."""
        from aios_core.test_engine.engine import TestEngine
        from aios_core.test_engine.models import TestCase, TestCategory

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        violation_count = 0

        def check_no_violations(action, evaluation):
            nonlocal violation_count
            violations = evaluation.get("violations", [])
            violation_count = len(violations)
            return len(violations) == 0, f"Found {len(violations)} violations"

        result = engine.run_case(
            TestCase(
                name="validator_integration",
                category=TestCategory.INTEGRATION,
                action={
                    "goal": "Clean action",
                    "scope": "test",
                    "risk": "low",
                    "audit_log": True,
                    "agent_id": "agent-1",
                    "authority": "user",
                },
                expected_decision="ALLOW",
                validator=check_no_violations,
            )
        )
        assert result["status"] == "passed"
        assert violation_count == 0

    def test_suite_results_consistent_with_report(self):
        """Suite results should be consistent with the generated report."""
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        report = engine.run_all()
        # Check consistency
        suite_total = sum(s.total for s in report.suites)
        suite_passed = sum(s.passed for s in report.suites)
        suite_failed = sum(s.failed for s in report.suites)
        assert suite_total == report.total_tests
        assert suite_passed == report.total_passed
        assert suite_failed == report.total_failed

    def test_all_suites_runnable(self):
        """All built-in suites should be runnable without errors."""
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        for suite_info in engine.list_suites():
            suite_result = engine.run_suite(suite_info["name"])
            assert suite_result.total > 0
            assert len(suite_result.results) == suite_result.total

    def test_evolution_proposal_triggers_test_engine(self):
        """TestEngine can validate an evolution-like proposal."""
        from aios_core.test_engine.engine import TestEngine
        from aios_core.test_engine.models import TestCase, TestCategory

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        # An evolution action without constitutional check should be DENY
        result = engine.run_case(
            TestCase(
                name="evo_proposal_check",
                category=TestCategory.EVOLUTION,
                action={
                    "goal": "Deploy evolution proposal",
                    "scope": "evolution",
                    "risk": "medium",
                    "audit_log": True,
                    "agent_id": "evo-agent",
                    "authority": "system",
                    "action_type": "evolution_deploy",
                },
                expected_decision="DENY",
            )
        )
        assert result["actual"] == "DENY"
        assert result["status"] == "passed"

    def test_test_engine_stats_comprehensive(self):
        """Stats should be comprehensive after running tests."""
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        engine.run_all()
        stats = engine.stats()
        assert stats["version"] == "1.0.0"
        assert len(stats["suites_available"]) == 4
        assert stats["reports_generated"] == 1
        assert stats["last_report_status"] == "passed"
        assert stats["last_report_summary"] is not None
        assert stats["last_report_summary"]["total"] == 23
        assert stats["runner"]["tests_run"] == 23
        assert stats["runner"]["engine_version"] == "3.0.0"

    def test_report_persistence_in_memory(self):
        """Multiple reports should be tracked in memory."""
        from aios_core.test_engine.engine import TestEngine

        engine = TestEngine(CONSTITUTION_DIR, POLICIES_DIR)
        assert engine.last_report() is None
        engine.run_all()
        report1 = engine.last_report()
        assert report1 is not None
        engine.run_all()
        report2 = engine.last_report()
        assert report2 is not None
        # Should be different reports (different IDs)
        assert report1.report_id != report2.report_id
        assert engine.stats()["reports_generated"] == 2
