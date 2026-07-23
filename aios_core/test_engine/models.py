"""AIOS Test Engine — Data Models v1.0.0

Defines test cases, test suites, test results, and test reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestSeverity(str, Enum):
    CRITICAL = "critical"  # System-breaking if fails
    HIGH = "high"  # Important functionality
    MEDIUM = "medium"  # Normal functionality
    LOW = "low"  # Edge cases, nice-to-haves


class TestCategory(str, Enum):
    CONSTITUTIONAL = "constitutional"  # Constitution compliance
    REGRESSION = "regression"  # Prevent behavior regressions
    INTEGRATION = "integration"  # Cross-subsystem integration
    PERFORMANCE = "performance"  # Timing/benchmark tests
    SECURITY = "security"  # Security policy enforcement
    EVOLUTION = "evolution"  # Evolution pipeline validation


@dataclass
class TestCase:
    """A single test case with expectation and optional validator."""

    name: str
    description: str = ""
    category: TestCategory = TestCategory.CONSTITUTIONAL
    severity: TestSeverity = TestSeverity.MEDIUM

    # The action to evaluate
    action: dict = field(default_factory=dict)

    # Expected outcome
    expected_decision: str = "ALLOW"  # ALLOW, DENY, REVIEW

    # Optional: custom validator function
    # If provided, called with (action, evaluation_result) -> (passed: bool, message: str)
    validator: Optional[Callable] = None

    # Optional: tags for filtering
    tags: list[str] = field(default_factory=list)

    # Timeout in seconds (default 30)
    timeout: float = 30.0

    # Retry count on failure (default 0)
    retries: int = 0


@dataclass
class TestResult:
    """Result of running a single test case."""

    test_name: str
    status: TestStatus = TestStatus.PENDING
    category: TestCategory = TestCategory.CONSTITUTIONAL
    severity: TestSeverity = TestSeverity.MEDIUM

    # What we got vs what we expected
    actual_decision: str | None = None
    expected_decision: str | None = None

    # Details
    message: str = ""
    evaluation: Optional[dict] = None  # Full evaluation result
    duration_ms: float = 0.0
    retry_count: int = 0
    error: str | None = None

    # Timestamps
    started_at: str | None = None
    completed_at: str | None = None


@dataclass
class TestSuiteResult:
    """Result of running a test suite."""

    suite_name: str
    status: TestStatus = TestStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0.0

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

    results: list[TestResult] = field(default_factory=list)

    # Breakdowns
    by_category: dict = field(default_factory=dict)
    by_severity: dict = field(default_factory=dict)


@dataclass
class TestReport:
    """Comprehensive test report across multiple suites."""

    report_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    total_suites: int = 0
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_errors: int = 0
    total_skipped: int = 0
    overall_status: str = "pending"
    duration_ms: float = 0.0

    suites: list[TestSuiteResult] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)  # Summary of failures
