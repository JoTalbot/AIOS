"""Tests for logging and monitoring infrastructure."""

from aios_core.logging_config import JSONFormatter
from aios_core.api.monitoring import AlertManager, PerformanceMonitor


def test_json_formatter():
    f = JSONFormatter()
    assert f is not None


def test_alert_manager_init():
    am = AlertManager()
    assert am is not None


def test_performance_monitor_init():
    pm = PerformanceMonitor()
    assert pm is not None
