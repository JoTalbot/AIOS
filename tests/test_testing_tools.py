"""Tests for test engine runner and suites."""

from aios_core.test_engine.runner import TestRunner
from aios_core.test_engine.suites import TestSuite


def test_test_runner_init():
    tr = TestRunner()
    assert tr is not None


def test_test_suite_init():
    ts = TestSuite("smoke")
    assert ts is not None
