"""AIOS Test Engine — Reporter v1.0.0

Generates test reports from suite results. Supports summary,
detailed, and failure-focused views.
"""

from __future__ import annotations

from .models import TestReport, TestStatus, TestSuiteResult


class TestReporter:
    """Generates test reports.

    Usage:
        reporter = TestReporter()
        report = reporter.generate("Full System Test", [suite_result1, suite_result2])
        print(reporter.summary_text(report))
        print(reporter.failures_text(report))
    """

    def generate(self, title: str, suites: list[TestSuiteResult]) -> TestReport:
        """Generate a comprehensive test report from suite results."""
        report = TestReport(report_id=_short_id())

        report.total_suites = len(suites)
        for suite in suites:
            report.suites.append(suite)
            report.total_tests += suite.total
            report.total_passed += suite.passed
            report.total_failed += suite.failed
            report.total_errors += suite.errors
            report.total_skipped += suite.skipped
            report.duration_ms += suite.duration_ms

        if report.total_failed == 0 and report.total_errors == 0:
            report.overall_status = "passed"
        elif report.total_passed == 0:
            report.overall_status = "failed"
        else:
            report.overall_status = "partial"

        # Collect failures
        for suite in suites:
            for r in suite.results:
                if r.status in (TestStatus.FAILED, TestStatus.ERROR):
                    report.failures.append(
                        {
                            "suite": suite.suite_name,
                            "test": r.test_name,
                            "status": r.status.value,
                            "message": r.message,
                            "expected": r.expected_decision,
                            "actual": r.actual_decision,
                            "duration_ms": r.duration_ms,
                        }
                    )

        return report

    def summary_text(self, report: TestReport) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"AIOS Test Report: {report.report_id}",
            f"{'=' * 50}",
            f"Overall: {report.overall_status.upper()}",
            (f"Suites: {report.total_suites}  "
            f"Tests: {report.total_tests}  "
            f"Passed: {report.total_passed}  "
            f"Failed: {report.total_failed}  "
            f"Errors: {report.total_errors}  "
            f"Skipped: {report.total_skipped}"),
            f"Duration: {report.duration_ms:.1f}ms",
            "",
        ]

        for suite in report.suites:
            status_icon = "PASS" if suite.status == TestStatus.PASSED else "FAIL"
            lines.append(
                f"  [{status_icon}] {suite.suite_name}: "
                f"{suite.passed}/{suite.total} passed "
                f"({suite.duration_ms:.1f}ms)"
            )

        if report.failures:
            lines.append(f"\n{len(report.failures)} FAILURES:")
            for f in report.failures[:10]:
                lines.append(f"  - {f['suite']}::{f['test']}: {f['message']}")  # noqa: PERF401

        return "\n".join(lines)

    def failures_text(self, report: TestReport) -> str:
        """Generate a failures-only report."""
        if not report.failures:
            return "No failures."

        lines = [f"FAILURES ({len(report.failures)}):"]
        for i, f in enumerate(report.failures, 1):
            lines.append(
                f"\n{i}. {f['suite']}::{f['test']}\n"
                f"   Status: {f['status']}\n"
                f"   Expected: {f['expected']}\n"
                f"   Actual: {f['actual']}\n"
                f"   Message: {f['message']}"
            )
        return "\n".join(lines)

    def to_dict(self, report: TestReport) -> dict:
        """Serialize report to dict for JSON persistence."""
        return {
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "overall_status": report.overall_status,
            "total_suites": report.total_suites,
            "total_tests": report.total_tests,
            "total_passed": report.total_passed,
            "total_failed": report.total_failed,
            "total_errors": report.total_errors,
            "total_skipped": report.total_skipped,
            "duration_ms": report.duration_ms,
            "failures_count": len(report.failures),
            "suites": [
                {
                    "name": s.suite_name,
                    "status": s.status.value,
                    "total": s.total,
                    "passed": s.passed,
                    "failed": s.failed,
                    "errors": s.errors,
                    "duration_ms": s.duration_ms,
                }
                for s in report.suites
            ],
        }


def _short_id() -> str:
    import uuid

    return uuid.uuid4().hex[:8]
