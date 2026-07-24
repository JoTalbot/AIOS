"""Tests for aios_core/self_healing.py"""
from __future__ import annotations
import pytest
from aios_core.self_healing import SelfHealing, HealthMonitor


@pytest.fixture()
def monitor():
    return HealthMonitor()


@pytest.fixture()
def healing():
    return SelfHealing(max_recovery_attempts=3, escalation_threshold=0.5)


class TestHealthMonitor:
    def test_register(self, monitor):
        monitor.register("db", check_fn=lambda: True)

    def test_run_all(self, monitor):
        monitor.register("s1", check_fn=lambda: True)
        monitor.register("s2", check_fn=lambda: False)
        results = monitor.run_all()
        assert isinstance(results, dict)

    def test_overall_healthy(self, monitor):
        monitor.register("ok", check_fn=lambda: True)
        assert isinstance(monitor.overall_healthy(), bool)

    def test_unhealthy_services(self, monitor):
        monitor.register("bad", check_fn=lambda: False)
        unhealthy = monitor.unhealthy_services()
        assert isinstance(unhealthy, list)


class TestSelfHealing:
    def test_register_strategy(self, healing):
        healing.register_strategy("ConnectionError", strategy=lambda err, ctx: "restarted")

    def test_register_health_check(self, healing):
        healing.register_health_check("api", check_fn=lambda: True)

    def test_heal_healthy(self, healing):
        healing.register_health_check("ok_service", check_fn=lambda: True)
        result = healing.heal(error=Exception("test"), context={})
        assert isinstance(result, (bool, dict))

    def test_diagnose(self, healing):
        result = healing.diagnose()
        assert isinstance(result, dict)

    def test_reset_attempts(self, healing):
        healing.reset_attempts()

    def test_stats(self, healing):
        s = healing.stats()
        assert isinstance(s, dict)
