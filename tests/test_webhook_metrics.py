"""Tests for webhook Prometheus metrics."""

import pytest
from aios_core.webhook_manager import WebhookManager
from aios_core.webhook_metrics import register_webhook_metrics, get_webhook_prometheus_text
from aios_core.metrics_exporter import MetricsExporter


class TestWebhookMetrics:
    @pytest.fixture
    def manager_with_webhooks(self):
        mgr = WebhookManager()
        mgr.register("slack", "https://hooks.slack.com/test", ["ban_detected", "low_success_rate"])
        mgr.register("teams", "https://teams.webhook/test", ["backup_completed"])
        mgr.notify("ban_detected", {"profile": "ig_shop_1"})
        mgr.notify("backup_completed", {"backup_id": "b1"})
        return mgr

    def test_register_webhook_metrics(self, manager_with_webhooks):
        # Should not raise
        register_webhook_metrics(manager_with_webhooks)

    def test_get_prometheus_text(self, manager_with_webhooks):
        text = get_webhook_prometheus_text(manager_with_webhooks)
        assert "aios_webhook_targets_total" in text
        assert "aios_webhook_targets_active" in text
        assert "aios_webhook_triggers_total" in text
        assert "aios_webhook_errors_total" in text
        assert "aios_webhook_history_size" in text
        assert "aios_webhook_target_triggers" in text
        assert "slack" in text
        assert "teams" in text

    def test_prometheus_text_without_manager(self):
        text = get_webhook_prometheus_text(None)
        assert "aios_webhook_targets_total" in text

    def test_metrics_values_correct(self, manager_with_webhooks):
        text = get_webhook_prometheus_text(manager_with_webhooks)
        # Should have 2 targets
        assert "aios_webhook_targets_total 2" in text
        # Should have 2 active
        assert "aios_webhook_targets_active 2" in text

    def test_per_target_metrics(self, manager_with_webhooks):
        text = get_webhook_prometheus_text(manager_with_webhooks)
        # Slack should have 1 trigger (ban_detected)
        assert 'target="slack"' in text
        # Teams should have 1 trigger (backup_completed)
        assert 'target="teams"' in text


class TestMetricsExporter:
    def test_counter_with_labels(self):
        exporter = MetricsExporter()
        exporter.inc_counter("test_counter", labels={"env": "prod"})
        exporter.inc_counter("test_counter", labels={"env": "prod"})
        exporter.inc_counter("test_counter", labels={"env": "dev"})
        assert exporter.counters.get('test_counter{env="dev"}') == 1.0
        assert exporter.counters.get('test_counter{env="prod"}') == 2.0

    def test_gauge_with_labels(self):
        exporter = MetricsExporter()
        exporter.set_gauge("test_gauge", 42.0, labels={"host": "server1"})
        assert exporter.gauges.get('test_gauge{host="server1"}') == 42.0

    def test_histogram(self):
        exporter = MetricsExporter()
        exporter.observe_histogram("request_duration", 0.5)
        exporter.observe_histogram("request_duration", 1.2)
        exporter.observe_histogram("request_duration", 0.3)
        assert len(exporter.histograms["request_duration"]) == 3

    def test_export_with_labels(self):
        exporter = MetricsExporter()
        exporter.inc_counter("requests", labels={"method": "GET"})
        exporter.set_gauge("connections", 10, labels={"host": "db1"})
        text = exporter.export()
        assert "requests" in text
        assert "connections" in text
        assert 'method="GET"' in text
        assert 'host="db1"' in text

    def test_stats(self):
        exporter = MetricsExporter()
        exporter.inc_counter("c1")
        exporter.set_gauge("g1", 1)
        exporter.observe_histogram("h1", 0.5)
        stats = exporter.stats()
        assert stats["counters"] == 1
        assert stats["gauges"] == 1
        assert stats["histograms"] == 1
