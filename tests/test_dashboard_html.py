"""Tests for dashboard and Ops HTML panel."""

from aios_core.dashboard import Dashboard


def test_dashboard_init():
    d = Dashboard()
    assert d is not None
