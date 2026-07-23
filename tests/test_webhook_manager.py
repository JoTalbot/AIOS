"""Tests for AIOS webhook notification system."""

import json
import pytest
from pathlib import Path
from aios_core.webhook_manager import (
    WebhookManager,
    WebhookTarget,
    WebhookPayload,
    WebhookEvent,
    notify_ban_detected,
    notify_backup_completed,
    notify_low_success_rate,
)


class TestWebhookTarget:
    def test_create_target(self):
        target = WebhookTarget(
            name="slack-alerts",
            url="https://hooks.slack.com/test",
            events=["ban_detected", "low_success_rate"],
        )
        assert target.name == "slack-alerts"
        assert target.active
        assert target.trigger_count == 0
        assert len(target.events) == 2

    def test_matches_event(self):
        target = WebhookTarget(
            name="test",
            url="https://example.com/hook",
            events=["ban_detected", "backup_completed"],
        )
        assert target.matches_event("ban_detected")
        assert target.matches_event("backup_completed")
        assert not target.matches_event("device_offline")

    def test_inactive_target_no_match(self):
        target = WebhookTarget(
            name="test",
            url="https://example.com/hook",
            events=["ban_detected"],
            active=False,
        )
        assert not target.matches_event("ban_detected")

    def test_to_dict(self):
        target = WebhookTarget(
            name="test",
            url="https://example.com/hook",
            events=["ban_detected"],
        )
        d = target.to_dict()
        assert d["name"] == "test"
        assert d["url"] == "https://example.com/hook"
        assert "events" in d


class TestWebhookPayload:
    def test_create_payload(self):
        payload = WebhookPayload(
            event="ban_detected",
            timestamp="2026-07-23T12:00:00",
            source="aios",
            data={"profile": "ig_shop_1"},
            severity="critical",
        )
        assert payload.event == "ban_detected"
        assert payload.severity == "critical"

    def test_payload_to_dict(self):
        payload = WebhookPayload(
            event="test",
            timestamp="2026-07-23T12:00:00",
            source="aios",
            data={"key": "value"},
        )
        d = payload.to_dict()
        assert d["event"] == "test"
        assert d["data"]["key"] == "value"

    def test_payload_sign(self):
        payload = WebhookPayload(
            event="test",
            timestamp="2026-07-23T12:00:00",
            source="aios",
            data={"key": "value"},
        )
        sig = payload.sign("my-secret")
        assert len(sig) == 64  # SHA-256 hex digest


class TestWebhookManager:
    def test_register_target(self):
        manager = WebhookManager()
        target = manager.register(
            "slack",
            "https://hooks.slack.com/test",
            ["ban_detected"],
        )
        assert "slack" in manager.targets
        assert target.name == "slack"

    def test_unregister_target(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", ["ban_detected"])
        assert manager.unregister("test")
        assert "test" not in manager.targets

    def test_unregister_nonexistent(self):
        manager = WebhookManager()
        assert not manager.unregister("nonexistent")

    def test_activate_deactivate(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", ["ban_detected"])
        assert manager.deactivate("test")
        assert not manager.targets["test"].active
        assert manager.activate("test")
        assert manager.targets["test"].active

    def test_notify(self):
        manager = WebhookManager()
        manager.register("slack", "https://hooks.slack.com/test", ["ban_detected"])
        manager.register("teams", "https://teams.webhook/test", ["low_success_rate"])

        result = manager.notify("ban_detected", {"profile": "ig_shop_1"}, severity="critical")
        assert result["targets_triggered"] == 1
        assert result["targets_skipped"] == 1

    def test_notify_no_matching_targets(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", ["ban_detected"])

        result = manager.notify("device_offline", {"device": "emulator-5554"})
        assert result["targets_triggered"] == 0
        assert result["targets_skipped"] == 1

    def test_notify_with_secret(self):
        manager = WebhookManager()
        manager.register(
            "signed",
            "https://example.com/hook",
            ["ban_detected"],
            secret="my-secret-key",
        )

        result = manager.notify("ban_detected", {"profile": "test"})
        assert result["targets_triggered"] == 1

    def test_on_event_handler(self):
        manager = WebhookManager()
        received = []

        def handler(payload):
            received.append(payload)

        manager.on_event("ban_detected", handler)
        manager.notify("ban_detected", {"profile": "test"})

        assert len(received) == 1
        assert received[0].event == "ban_detected"

    def test_list_targets(self):
        manager = WebhookManager()
        manager.register("slack", "https://hooks.slack.com/test", ["ban_detected"])
        manager.register("teams", "https://teams.webhook/test", ["backup_completed"])

        targets = manager.list_targets()
        assert len(targets) == 2

    def test_get_history(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", ["ban_detected", "device_offline"])

        manager.notify("ban_detected", {"p": "1"})
        manager.notify("device_offline", {"d": "em1"})
        manager.notify("ban_detected", {"p": "2"})

        history = manager.get_history()
        assert len(history) == 3

        # Filter by event
        ban_history = manager.get_history(event="ban_detected")
        assert len(ban_history) == 2

    def test_get_history_limit(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", ["ban_detected"])

        for i in range(10):
            manager.notify("ban_detected", {"i": i})

        history = manager.get_history(limit=5)
        assert len(history) == 5

    def test_health_report(self):
        manager = WebhookManager()
        manager.register("active1", "https://example.com/1", ["ban_detected"])
        manager.register("active2", "https://example.com/2", ["ban_detected"])
        manager.deactivate("active2")

        report = manager.health_report()
        assert report["total_targets"] == 2
        assert report["active_targets"] == 1
        assert report["inactive_targets"] == 1

    def test_test_webhook(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com/hook", ["custom"])

        result = manager.test_webhook("test")
        assert result["status"] == "test_sent"

    def test_test_webhook_not_found(self):
        manager = WebhookManager()
        result = manager.test_webhook("nonexistent")
        assert "error" in result

    def test_export_import_config(self, tmp_path):
        manager = WebhookManager()
        manager.register("slack", "https://hooks.slack.com/test", ["ban_detected"])
        manager.register("teams", "https://teams.webhook/test", ["backup_completed"])

        config_path = tmp_path / "webhooks.json"
        count = manager.export_config(str(config_path))
        assert count == 2

        # Import into new manager
        manager2 = WebhookManager()
        imported = manager2.import_config(str(config_path))
        assert imported == 2
        assert "slack" in manager2.targets
        assert "teams" in manager2.targets


class TestConvenienceFunctions:
    def test_notify_ban_detected(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", [WebhookEvent.BAN_DETECTED])
        result = notify_ban_detected("ig_shop_1", "rate_limit_exceeded", manager)
        assert result["targets_triggered"] == 1

    def test_notify_backup_completed(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", [WebhookEvent.BACKUP_COMPLETED])
        result = notify_backup_completed("backup_123", 45.2, manager)
        assert result["targets_triggered"] == 1

    def test_notify_low_success_rate(self):
        manager = WebhookManager()
        manager.register("test", "https://example.com", [WebhookEvent.LOW_SUCCESS_RATE])
        result = notify_low_success_rate("ig_shop_2", 75.0, 80.0, manager)
        assert result["targets_triggered"] == 1


class TestWebhookEvent:
    def test_event_values(self):
        assert WebhookEvent.BAN_DETECTED == "ban_detected"
        assert WebhookEvent.LOW_SUCCESS_RATE == "low_success_rate"
        assert WebhookEvent.DEVICE_OFFLINE == "device_offline"
        assert WebhookEvent.BACKUP_COMPLETED == "backup_completed"
        assert WebhookEvent.KEY_ROTATED == "key_rotated"
