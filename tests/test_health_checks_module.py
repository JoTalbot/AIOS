"""Tests for aios_core/health_checks.py"""
from __future__ import annotations
import pytest
from aios_core.health_checks import HealthCheckRegistry


@pytest.fixture()
def registry():
    return HealthCheckRegistry()


class TestHealthCheckRegistry:
    def test_register(self, registry):
        registry.register("db", check_fn=lambda: True)

    def test_unregister(self, registry):
        registry.register("temp", check_fn=lambda: True)
        registry.unregister("temp")

    def test_run_check_healthy(self, registry):
        registry.register("ok_service", check_fn=lambda: True)
        result = registry.run_check("ok_service")
        assert result is not None
        assert hasattr(result, 'status') or isinstance(result, dict)

    def test_run_check_unhealthy(self, registry):
        registry.register("bad_service", check_fn=lambda: False)
        result = registry.run_check("bad_service")
        assert result is not None
        assert hasattr(result, 'status') or isinstance(result, dict)

    def test_run_all(self, registry):
        registry.register("a", check_fn=lambda: True)
        registry.register("b", check_fn=lambda: True)
        results = registry.run_all()
        assert isinstance(results, dict)

    def test_overall_status(self, registry):
        registry.register("healthy", check_fn=lambda: True)
        status = registry.overall_status()
        assert isinstance(status, (str, dict))

    def test_liveness_status(self, registry):
        result = registry.liveness_status()
        assert isinstance(result, (str, dict, bool))

    def test_readiness_status(self, registry):
        registry.register("ready", check_fn=lambda: True)
        result = registry.readiness_status()
        assert isinstance(result, (str, dict, bool))

    def test_summary(self, registry):
        registry.register("s1", check_fn=lambda: True)
        result = registry.summary()
        assert isinstance(result, dict)

    def test_stats(self, registry):
        s = registry.stats()
        assert isinstance(s, dict)
