"""Tests for distributed, workflow, and scheduling infrastructure."""

from aios_core.distributed_queue import DistributedQueue
from aios_core.workflow import WorkflowEngine
from aios_core.health_checks import HealthChecker
from aios_core.metrics_exporter import MetricsExporter
from aios_core.chaos import ChaosMonkey


def test_distributed_queue_stats():
    s = DistributedQueue().stats()
    assert isinstance(s, dict)


def test_workflow_engine_stats():
    s = WorkflowEngine().stats()
    assert isinstance(s, dict)


def test_health_checker_stats():
    s = HealthChecker().stats()
    assert isinstance(s, dict)


def test_metrics_exporter_stats():
    s = MetricsExporter().stats()
    assert isinstance(s, dict)


def test_chaos_monkey_stats():
    s = ChaosMonkey().stats()
    assert isinstance(s, dict)
