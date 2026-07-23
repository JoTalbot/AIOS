"""Tests for web UI, webhook metrics, and telemetry."""

from aios_core.webhook_metrics import WebhookMetrics
from aios_core.telemetry import Telemetry
from aios_core.metrics_exporter import MetricsExporter


def test_webhook_metrics_init():
    wm = WebhookMetrics()
    assert wm is not None


def test_telemetry_init():
    t = Telemetry()
    assert t is not None


def test_metrics_exporter_init():
    me = MetricsExporter()
    assert me is not None
