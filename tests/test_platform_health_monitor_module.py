"""Tests for aios_core/platform_health_monitor.py"""
from __future__ import annotations
import pytest
from aios_core.platform_health_monitor import PlatformHealthMonitor


@pytest.fixture()
def monitor():
    return PlatformHealthMonitor()


class TestPlatformHealthMonitor:
    def test_register_platform(self, monitor):
        monitor.register_platform("olx")
        health = monitor.get_health("olx")
        assert health is not None

    def test_report_success(self, monitor):
        monitor.register_platform("instagram")
        monitor.report_success("instagram", latency_ms=150)

    def test_report_failure(self, monitor):
        monitor.register_platform("facebook")
        monitor.report_failure("facebook", error="timeout")

    def test_report_block(self, monitor):
        monitor.register_platform("tiktok")
        monitor.report_block("tiktok", block_type="rate_limit")

    def test_get_health(self, monitor):
        monitor.register_platform("olx")
        monitor.report_success("olx")
        health = monitor.get_health("olx")
        assert health is not None

    def test_get_health_unknown(self, monitor):
        result = monitor.get_health("unknown_platform")
        assert result is None or isinstance(result, dict)

    def test_get_all_health(self, monitor):
        monitor.register_platform("a")
        monitor.register_platform("b")
        all_h = monitor.get_all_health()
        assert isinstance(all_h, (dict, list))

    def test_compare_platforms(self, monitor):
        monitor.register_platform("a")
        monitor.register_platform("b")
        monitor.report_success("a")
        monitor.report_success("b")
        result = monitor.compare_platforms()
        assert isinstance(result, (list, dict))

    def test_detect_degradation(self, monitor):
        monitor.register_platform("degrading")
        for _ in range(5):
            monitor.report_failure("degrading", error="err")
        result = monitor.detect_degradation()
        assert isinstance(result, (list, dict))

    def test_best_platform(self, monitor):
        monitor.register_platform("fast")
        monitor.register_platform("slow")
        monitor.report_success("fast", latency_ms=50)
        monitor.report_success("slow", latency_ms=500)
        best = monitor.best_platform()
        assert best is not None or isinstance(best, (str, dict))

    def test_stats(self, monitor):
        s = monitor.stats()
        assert isinstance(s, dict)
