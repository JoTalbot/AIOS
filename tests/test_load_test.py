"""Tests for load testing framework."""

from aios_core.load_testing import LoadTester


def test_tester_init():
    lt = LoadTester()
    assert lt is not None


def test_run_with_fast_func():
    lt = LoadTester()
    result = lt.run(lambda: None, concurrent_users=2, duration_seconds=1)
    assert isinstance(result, dict)
