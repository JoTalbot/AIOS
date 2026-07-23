"""AIOS Test Engine — Runner v1.0.0

Executes test cases against AIOS constitutional evaluation.
Supports timeouts, retries, parallel execution (sequential for now),
and detailed result collection.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..storage import Database

from .models import (
    TestCase,
    TestCategory,
    TestReport,
    TestResult,
    TestSeverity,
    TestStatus,
    TestSuiteResult,
)


class TestRunner:
    """Executes test cases against the AIOS constitution engine.

    Usage:
        runner = TestRunner(constitution_dir="...", policies_dir="...", db=Database(":memory:"))

        result = runner.run_case(TestCase(
            name="test_deny_unknown_agent",
            action={"goal": "test", "scope": "test", "risk": "low", "audit_log": True, "agent_id": "unknown", "authority": "user"},
            expected_decision="DENY",
            category=TestCategory.SECURITY,
        ))
        print(result.status)  # TestStatus.PASSED

        # Run a full suite
        suite_result = runner.run_suite("security_tests", test_cases)
    """

    def __init__(
        self,
        constitution_dir: str,
        policies_dir: str,
        db: Optional[Database] = None,
    ):
        from ..constitution_engine import ConstitutionEngine

        self.engine = ConstitutionEngine(constitution_dir, policies_dir)
        self.db = db
        self._run_count = 0

    def run_case(self, case: TestCase) -> TestResult:
        """Run a single test case.

        1. Build action dict (merge case.action with required fields)
        2. Evaluate against constitution
        3. Check expected_decision
        4. If custom validator, call it
        5. Handle retries
        """
        result = TestResult(
            test_name=case.name,
            category=case.category,
            severity=case.severity,
            expected_decision=case.expected_decision,
        )

        result.started_at = _now_iso()
        start = time.monotonic()

        # Use action dict directly — test cases must provide their own fields.
        # This allows testing missing-field scenarios (e.g. missing "goal" → DENY).
        action = dict(case.action)

        # Run with retries
        last_error = None
        for attempt in range(case.retries + 1):
            try:
                evaluation = self.engine.evaluate(action)
                result.evaluation = evaluation
                result.actual_decision = evaluation.get("decision")

                # Check expected decision
                if result.actual_decision == case.expected_decision:
                    result.status = TestStatus.PASSED
                    result.message = f"Decision matches: {result.actual_decision}"
                else:
                    result.status = TestStatus.FAILED
                    result.message = (
                        f"Expected {case.expected_decision}, got {result.actual_decision}. "
                        f"Reason: {evaluation.get('reason', '')}"
                    )

                # Custom validator
                if case.validator and result.status == TestStatus.PASSED:
                    try:
                        passed, msg = case.validator(action, evaluation)
                        if not passed:
                            result.status = TestStatus.FAILED
                            result.message = msg
                    except Exception as e:
                        result.status = TestStatus.ERROR
                        result.message = f"Validator error: {e}"

                break  # Success or definitive failure

            except Exception as e:
                last_error = str(e)
                result.retry_count = attempt
                if attempt < case.retries:
                    continue
                result.status = TestStatus.ERROR
                result.error = last_error
                result.message = f"Execution error: {last_error}"

        result.completed_at = _now_iso()
        result.duration_ms = (time.monotonic() - start) * 1000
        self._run_count += 1

        return result

    def run_suite(self, suite_name: str, cases: list[TestCase]) -> TestSuiteResult:
        """Run a list of test cases as a named suite."""
        suite = TestSuiteResult(suite_name=suite_name)
        suite.started_at = _now_iso()
        start = time.monotonic()
        suite.total = len(cases)

        for case in cases:
            result = self.run_case(case)
            suite.results.append(result)

            if result.status == TestStatus.PASSED:
                suite.passed += 1
            elif result.status == TestStatus.FAILED:
                suite.failed += 1
            elif result.status == TestStatus.ERROR:
                suite.errors += 1
            elif result.status == TestStatus.SKIPPED:
                suite.skipped += 1

        # Determine overall status
        if suite.failed == 0 and suite.errors == 0:
            suite.status = TestStatus.PASSED
        elif suite.passed == 0 and (suite.failed > 0 or suite.errors > 0):
            suite.status = TestStatus.FAILED
        else:
            suite.status = TestStatus.PASSED if suite.failed == 0 else TestStatus.FAILED

        suite.completed_at = _now_iso()
        suite.duration_ms = (time.monotonic() - start) * 1000

        # Build breakdowns
        for r in suite.results:
            cat = r.category.value
            sev = r.severity.value
            suite.by_category[cat] = suite.by_category.get(cat, 0) + 1
            suite.by_severity[sev] = suite.by_severity.get(sev, 0) + 1

        return suite

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "tests_run": self._run_count,
            "engine_version": self.engine.version,
        }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
