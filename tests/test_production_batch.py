"""Tests for Production Autopilot and Webhook Bridge."""

from aios_core.production_autopilot import ProductionAutopilot


def test_autopilot_stats():
    pa = ProductionAutopilot()
    s = pa.stats()
    assert isinstance(s, dict)
