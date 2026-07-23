"""Tests for AI safety dashboard and monitor."""

from aios_core.ai_safety_dashboard import SafetyDashboard
from aios_core.ai_safety_monitoring import SafetyMonitor


def test_dashboard_init():
    sd = SafetyDashboard()
    assert sd is not None


def test_monitor_init():
    sm = SafetyMonitor()
    assert sm is not None


def test_monitor_stats():
    sm = SafetyMonitor()
    s = sm.stats()
    assert isinstance(s, dict)
