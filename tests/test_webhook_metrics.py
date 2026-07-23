"""Tests for webhook Prometheus metrics."""

import pytest
from aios_core.webhook_manager import WebhookManager
from aios_core.webhook_metrics import (
    register_webhook_metrics,
    get_webhook_prometheus_text,
)


class TestWebhookMetrics:
    def test_register_webhook_metrics_empty(self):
        """Test registering metrics with empty webhook manager."""
        manager = WebhookManager()
        # Should not raise
        register_webhook_metrics(manager)

    def test_register_webhook_metrics_with_targets(self):
        """Test registering metrics with webhook targets."""
        manager = WebhookManager()
        manager.register("slack", "https://hooks.slack.com/test", ["ban_detected"])
        manager.register("teams", "https://teams.webhook/test", ["backup_completed"])

        # Should not raise
        register_webhook_metrics(manager)

    def test_get_webhook_prometheus_text_empty(self):
        """Test Prometheus text output with no webhooks."""
        manager = WebhookManager()
        text = get_webhook_prometheus_text(manager)

        assert "aios_webhook_targets_total" in text
        assert "aios_webhook_targets_active" in text
        assert "aios_webhook_triggers_total" in text
        assert "aios_webhook_errors_total" in text
        assert "aios_webhook_history_size" in text

    def test_get_webhook_prometheus_text_with_targets(self):
        """Test Prometheus text output with webhook targets."""
        manager = WebhookManager()
        manager.register("slack", "https://hooks.slack.com/test", ["ban_detected"])
        manager.register("teams", "https://teams.webhook/test", ["backup_completed"])

        # Trigger some notifications
        manager.notify("ban_detected", {"profile": "ig_shop_1"})
        manager.notify("backup_completed", {"backup_id": "backup_123"})

        text = get_webhook_prometheus_text(manager)

        # Check metrics presence
        assert "aios_webhook_targets_total 2" in text
        assert "aios_webhook_targets_active 2" in text
        assert "aios_webhook_triggers_total" in text
        assert "aios_webhook_history_size" in text

        # Check per-target metrics
        assert 'target="slack"' in text
        assert 'target="teams"' in text

    def test_webhook_metrics_after_deactivation(self):
        """Test metrics after deactivating a webhook."""
        manager = WebhookManager()
        manager.register("slack", "https://hooks.slack.com/test", ["ban_detected"])
        manager.register("teams", "https://teams.webhook/test", ["backup_completed"])

        # Deactivate one
        manager.deactivate("teams")

        text = get_webhook_prometheus_text(manager)

        assert "aios_webhook_targets_total 2" in text
        assert "aios_webhook_targets_active 1" in text
        assert "aios_webhook_targets_inactive 1" in text

    def test_webhook_metrics_format(self):
        """Test that Prometheus output has correct format."""
        manager = WebhookManager()
        manager.register("test", "https://example.com/hook", ["ban_detected"])

        text = get_webhook_prometheus_text(manager)
        lines = text.split("\n")

        # Check for HELP and TYPE comments
        help_lines = [l for l in lines if l.startswith("# HELP")]
        type_lines = [l for l in lines if l.startswith("# TYPE")]

        assert len(help_lines) > 0
        assert len(type_lines) > 0

        # Check format of metric lines
        metric_lines = [l for l in lines if l and not l.startswith("#")]
        for line in metric_lines:
            # Should have name and value
            parts = line.split()
            assert len(parts) >= 2

    def test_register_webhook_metrics_multiple_times(self):
        """Test that registering metrics multiple times doesn't cause issues."""
        manager = WebhookManager()
        manager.register("test", "https://example.com/hook", ["ban_detected"])

        # Register multiple times
        register_webhook_metrics(manager)
        register_webhook_metrics(manager)
        register_webhook_metrics(manager)

        text = get_webhook_prometheus_text(manager)
        # Should still have correct count
        assert "aios_webhook_targets_total 1" in text

    def test_webhook_metrics_with_errors(self):
        """Test metrics when webhooks have errors."""
        manager = WebhookManager()
        target = manager.register("test", "https://example.com/hook", ["ban_detected"])

        # Simulate error
        target.error_count = 5
        target.trigger_count = 10

        text = get_webhook_prometheus_text(manager)

        assert "aios_webhook_triggers_total" in text
        assert "aios_webhook_errors_total" in text
        assert 'target="test"' in text
