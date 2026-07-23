"""Tests for task scheduling, API versioning, and chaos testing."""

from aios_core.task_scheduler import TaskScheduler
from aios_core.api_versioning import APIVersioning
from aios_core.chaos_testing import ChaosTester


def test_task_scheduler_stats():
    ts = TaskScheduler()
    s = ts.stats()
    assert isinstance(s, dict)


def test_api_versioning_stats():
    av = APIVersioning()
    assert av is not None


def test_chaos_tester_stats():
    ct = ChaosTester()
    s = ct.stats()
    assert isinstance(s, dict)
