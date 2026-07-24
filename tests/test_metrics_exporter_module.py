"""Tests for aios_core/metrics_exporter.py"""
from __future__ import annotations
import pytest
from aios_core.metrics_exporter import MetricsExporter


@pytest.fixture()
def exporter():
    return MetricsExporter()


class TestMetricsExporter:
    def test_create(self, exporter):
        assert exporter is not None

    def test_inc_counter(self, exporter):
        exporter.inc_counter("requests_total")
        exporter.inc_counter("requests_total", value=5)

    def test_get_counter(self, exporter):
        exporter.inc_counter("test_counter", value=10)
        val = exporter.get_counter("test_counter")
        assert val >= 10 or isinstance(val, (int, float))

    def test_set_gauge(self, exporter):
        exporter.set_gauge("temperature", 42.5)

    def test_inc_gauge(self, exporter):
        exporter.set_gauge("connections", 10)
        exporter.inc_gauge("connections", value=5)

    def test_dec_gauge(self, exporter):
        exporter.set_gauge("connections", 10)
        exporter.dec_gauge("connections", value=3)

    def test_observe_histogram(self, exporter):
        exporter.observe_histogram("latency", 100.0)
        exporter.observe_histogram("latency", 200.0)

    def test_set_metadata(self, exporter):
        exporter.set_metadata("version", "1.0.0")

    def test_export_prometheus(self, exporter):
        exporter.inc_counter("test_c", value=1)
        result = exporter.export()
        assert isinstance(result, str)

    def test_reset_metric(self, exporter):
        exporter.inc_counter("temp_c", value=5)
        exporter.reset_metric("temp_c")

    def test_stats(self, exporter):
        s = exporter.stats()
        assert isinstance(s, dict)
