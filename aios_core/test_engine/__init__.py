"""AIOS Test Engine v1.0.0

Self-validation engine that runs constitutional compliance tests,
security policy tests, evolution safety tests, and integration tests
against the AIOS Constitution Engine.
"""

from .engine import TestEngine
from .models import (
    TestCase,
    TestCategory,
    TestReport,
    TestResult,
    TestSeverity,
    TestStatus,
    TestSuiteResult,
)
from .reporter import TestReporter
from .runner import TestRunner
from .suites import (
    constitutional_compliance_suite,
    evolution_safety_suite,
    integration_suite,
    security_policy_suite,
)

__all__ = [
    "TestCase",
    "TestResult",
    "TestSuiteResult",
    "TestReport",
    "TestStatus",
    "TestSeverity",
    "TestCategory",
    "TestRunner",
    "TestReporter",
    "TestEngine",
    "constitutional_compliance_suite",
    "security_policy_suite",
    "evolution_safety_suite",
    "integration_suite",
]
