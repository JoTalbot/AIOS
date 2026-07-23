"""AIOS Test Engine v1.0.0

Main facade that combines TestRunner, built-in suites, and reporting
into a single entry point for running all AIOS self-tests.

This engine is used by the Evolution pipeline (Phase 3) to validate
proposals, and by the Orchestrator for continuous self-validation.
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage import Database

from .models import TestSuiteResult, TestReport, TestCase
from .runner import TestRunner
from .suites import (
    constitutional_compliance_suite,
    security_policy_suite,
    evolution_safety_suite,
    integration_suite,
)
from .reporter import TestReporter

# Registry of all built-in suites
_BUILTIN_SUITES = {
    "constitutional_compliance": constitutional_compliance_suite,
    "security_policy": security_policy_suite,
    "evolution_safety": evolution_safety_suite,
    "integration": integration_suite,
}


class TestEngine:
    """Main test engine facade.

    Runs built-in and custom test suites against the AIOS constitution,
    producing comprehensive reports.

    Usage:
        engine = TestEngine(
            constitution_dir="docs/constitution",
            policies_dir="policies",
            db=Database(":memory:"),
        )

        # Run all built-in suites
        report = engine.run_all()
        print(engine.report_text(report))

        # Run specific suite
        suite_result = engine.run_suite("constitutional_compliance")

        # Run custom cases
        from test_engine.models import TestCase, TestCategory
        custom = TestCase(name="my_test", action={...}, expected_decision="ALLOW")
        result = engine.run_case(custom)
    """

    def __init__(
        self,
        constitution_dir: str,
        policies_dir: str,
        db: Optional[Database] = None,
    ):
        self.runner = TestRunner(constitution_dir, policies_dir, db)
        self.reporter = TestReporter()
        self._custom_suites: dict[str, list[TestCase]] = {}
        self._reports: list[TestReport] = []

    def run_case(self, case: TestCase) -> dict:
        """Run a single custom test case."""
        from .models import TestStatus

        result = self.runner.run_case(case)
        return {
            "name": result.test_name,
            "status": result.status.value,
            "expected": result.expected_decision,
            "actual": result.actual_decision,
            "message": result.message,
            "duration_ms": result.duration_ms,
        }

    def run_suite(self, suite_name: str) -> TestSuiteResult:
        """Run a built-in or custom suite by name."""
        # Check built-in suites
        if suite_name in _BUILTIN_SUITES:
            cases = _BUILTIN_SUITES[suite_name]()
        elif suite_name in self._custom_suites:
            cases = self._custom_suites[suite_name]
        else:
            raise ValueError(f"Unknown test suite: {suite_name}")

        return self.runner.run_suite(suite_name, cases)

    def run_all(self) -> TestReport:
        """Run all built-in suites and generate a comprehensive report."""
        suite_names = list(_BUILTIN_SUITES.keys())
        results = []
        for name in suite_names:
            suite_result = self.run_suite(name)
            results.append(suite_result)

        report = self.reporter.generate("AIOS Full Self-Test", results)
        self._reports.append(report)

        # Optionally persist report
        if self.runner.db:
            self.runner.db.execute(
                """INSERT INTO memory_items
                   (id, category, content, tags, source, confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.runner.db.new_id(),
                    "operational",
                    self.runner.db.to_json(self.reporter.to_dict(report)),
                    "test_report,self_test",
                    "test_engine",
                    1.0,
                    report.generated_at,
                ),
            )

        return report

    def register_suite(self, name: str, cases: list[TestCase]) -> None:
        """Register a custom test suite."""
        self._custom_suites[name] = cases

    def list_suites(self) -> list[dict]:
        """List all available suites (built-in + custom)."""
        result = []
        for name in _BUILTIN_SUITES:
            result.append({"name": name, "type": "builtin"})
        for name in self._custom_suites:
            result.append({"name": name, "type": "custom"})
        return result

    def report_text(self, report: TestReport) -> str:
        """Generate human-readable report text."""
        return self.reporter.summary_text(report)

    def failures_text(self, report: TestReport) -> str:
        """Generate failures-only text."""
        return self.reporter.failures_text(report)

    def last_report(self) -> Optional[TestReport]:
        """Get the most recent report."""
        return self._reports[-1] if self._reports else None

    def stats(self) -> dict:
        """Test engine statistics."""
        runner_stats = self.runner.stats()
        last = self.last_report()
        return {
            "version": "1.0.0",
            "suites_available": self.list_suites(),
            "reports_generated": len(self._reports),
            "last_report_status": last.overall_status if last else None,
            "last_report_summary": (
                {
                    "total": last.total_tests if last else 0,
                    "passed": last.total_passed if last else 0,
                    "failed": last.total_failed if last else 0,
                }
                if last
                else None
            ),
            "runner": runner_stats,
        }
