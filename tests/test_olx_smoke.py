"""Tests for OLX module functions — batch smoke coverage."""

from aios_core.modules.olx.analytics import AnalyticsCollector
from aios_core.modules.olx.autowatch import AutoWatch
from aios_core.modules.olx.bootstrap import OLXBootstrap
from aios_core.modules.olx.promotion import AdImprover


def test_analytics_collector_stats():
    ac = AnalyticsCollector()
    s = ac.stats()
    assert isinstance(s, dict)


def test_autowatch_init():
    aw = AutoWatch()
    assert aw is not None


def test_bootstrap_init():
    bt = OLXBootstrap()
    assert bt is not None


def test_ad_improver_stats():
    ai = AdImprover()
    assert ai is not None
