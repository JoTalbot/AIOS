"""Tests for aios_core/observability.py"""
from __future__ import annotations
import pytest
from aios_core.observability import Observability, MetricKind


@pytest.fixture()
def obs():
    return Observability()


class TestObservability:
    def test_register_metric(self, obs):
        obs.register_metric("requests_total", kind=MetricKind.COUNTER)
        assert obs.get_metric("requests_total") is not None

    def test_record_metric(self, obs):
        obs.register_metric("latency", kind=MetricKind.HISTOGRAM)
        obs.record_metric("latency", 42.0)

    def test_increment(self, obs):
        obs.register_metric("hits", kind=MetricKind.COUNTER)
        obs.increment("hits")

    def test_observe_histogram(self, obs):
        obs.register_metric("duration", kind=MetricKind.HISTOGRAM)
        obs.observe_histogram("duration", 100.0)

    def test_get_metric_nonexistent(self, obs):
        result = obs.get_metric("nope")
        assert result is None or result == 0.0

    def test_get_all_metrics(self, obs):
        obs.register_metric("m1", kind=MetricKind.COUNTER)
        metrics = obs.get_all_metrics()
        assert isinstance(metrics, dict)

    def test_start_trace(self, obs):
        trace = obs.start_trace("test_trace")
        assert trace is not None

    def test_log(self, obs):
        obs.log(level="INFO", message="test message")

    def test_get_logs(self, obs):
        obs.log(level="INFO", message="test")
        logs = obs.get_logs()
        assert isinstance(logs, list)

    def test_export_prometheus(self, obs):
        obs.register_metric("test_c", kind=MetricKind.COUNTER)
        obs.increment("test_c")
        result = obs.export_prometheus()
        assert isinstance(result, str)

    def test_stats(self, obs):
        s = obs.stats()
        assert isinstance(s, dict)
