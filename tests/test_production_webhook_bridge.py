"""Tests for Production Autopilot Webhook Bridge."""

import pytest
from aios_core.webhook_manager import WebhookManager, WebhookEvent
from aios_core.production_webhook_bridge import (
    ProductionWebhookBridge,
    get_production_bridge,
)


@pytest.fixture
def webhook_manager():
    return WebhookManager()


@pytest.fixture
def bridge(webhook_manager):
    return ProductionWebhookBridge(webhook_manager)


class TestProductionWebhookBridge:
    def test_on_ban_detected(self, bridge, webhook_manager):
        webhook_manager.register("slack", "https://hooks.slack.com/test", [WebhookEvent.BAN_DETECTED])
        result = bridge.on_ban_detected("ig_shop_1", "rate_limit")
        assert result["targets_triggered"] == 1

    def test_on_ban_detected_with_details(self, bridge, webhook_manager):
        webhook_manager.register("teams", "https://teams.webhook/test", [WebhookEvent.BAN_DETECTED])
        result = bridge.on_ban_detected("ig_shop_1", "rate_limit", {"actions": 45, "device": "emulator-5554"})
        assert result["targets_triggered"] == 1

    def test_on_low_success_rate(self, bridge, webhook_manager):
        webhook_manager.register("alerts", "https://alerts.example.com", [WebhookEvent.LOW_SUCCESS_RATE])
        result = bridge.on_low_success_rate("ig_shop_2", 0.75, 0.80)
        assert result["targets_triggered"] == 1

    def test_on_device_offline(self, bridge, webhook_manager):
        webhook_manager.register("monitoring", "https://monitor.example.com", [WebhookEvent.DEVICE_OFFLINE])
        result = bridge.on_device_offline("emulator-5554", "ig_shop_1")
        assert result["targets_triggered"] == 1

    def test_on_compliance_blocked(self, bridge, webhook_manager):
        webhook_manager.register("compliance", "https://compliance.example.com", [WebhookEvent.COMPLIANCE_BLOCKED])
        result = bridge.on_compliance_blocked("ig_shop_1", "send_message", "deny-by-default")
        assert result["targets_triggered"] == 1

    def test_on_backup_completed(self, bridge, webhook_manager):
        webhook_manager.register("backup-hook", "https://backup.example.com", [WebhookEvent.BACKUP_COMPLETED])
        result = bridge.on_backup_completed("backup_20260723", 45.2)
        assert result["targets_triggered"] == 1

    def test_on_backup_failed(self, bridge, webhook_manager):
        webhook_manager.register("backup-hook", "https://backup.example.com", [WebhookEvent.BACKUP_FAILED])
        result = bridge.on_backup_failed("Disk full")
        assert result["targets_triggered"] == 1

    def test_on_daily_report(self, bridge, webhook_manager):
        webhook_manager.register("daily", "https://daily.example.com", ["daily_report"])
        report = {
            "date": "Day 7",
            "total_cycles": 24,
            "total_actions": 1080,
            "avg_success_rate": 0.93,
            "bans": 0,
            "drifts": 1,
        }
        result = bridge.on_daily_report(report)
        assert result["targets_triggered"] == 1

    def test_on_simulation_complete(self, bridge, webhook_manager):
        webhook_manager.register("sim", "https://sim.example.com", ["simulation_complete"])
        summary = {
            "simulation": {
                "days": 14,
                "profiles": 3,
                "total_cycles": 1008,
                "avg_success_rate": 0.933,
                "bans": 0,
                "ban_free": True,
                "ga_criteria_met": True,
            }
        }
        result = bridge.on_simulation_complete(summary)
        assert result["targets_triggered"] == 1

    def test_on_key_rotated(self, bridge, webhook_manager):
        webhook_manager.register("keys", "https://keys.example.com", [WebhookEvent.KEY_ROTATED])
        result = bridge.on_key_rotated("admin", "aios_abc...", "aios_xyz...")
        assert result["targets_triggered"] == 1

    def test_on_key_revoked(self, bridge, webhook_manager):
        webhook_manager.register("keys", "https://keys.example.com", [WebhookEvent.KEY_REVOKED])
        result = bridge.on_key_revoked("admin", "aios_abc...", "compromised")
        assert result["targets_triggered"] == 1

    def test_disabled_bridge(self, webhook_manager):
        webhook_manager.register("test", "https://test.com", [WebhookEvent.BAN_DETECTED])
        bridge = ProductionWebhookBridge(webhook_manager)
        bridge.enabled = False
        result = bridge.on_ban_detected("ig_shop_1", "test")
        assert result is None

    def test_multiple_targets(self, bridge, webhook_manager):
        webhook_manager.register("slack", "https://hooks.slack.com", [WebhookEvent.BAN_DETECTED])
        webhook_manager.register("teams", "https://teams.webhook", [WebhookEvent.BAN_DETECTED])
        webhook_manager.register("pager", "https://pager.example.com", [WebhookEvent.BAN_DETECTED])

        result = bridge.on_ban_detected("ig_shop_1", "rate_limit")
        assert result["targets_triggered"] == 3

    def test_selective_subscription(self, bridge, webhook_manager):
        webhook_manager.register("ban-only", "https://ban.example.com", [WebhookEvent.BAN_DETECTED])
        webhook_manager.register("backup-only", "https://backup.example.com", [WebhookEvent.BACKUP_COMPLETED])

        # Ban should only trigger ban-only
        ban_result = bridge.on_ban_detected("ig_shop_1", "test")
        assert ban_result["targets_triggered"] == 1

        # Backup should only trigger backup-only
        backup_result = bridge.on_backup_completed("backup_123", 10.0)
        assert backup_result["targets_triggered"] == 1


class TestGetProductionBridge:
    def test_singleton(self):
        import aios_core.production_webhook_bridge as mod
        mod._production_bridge = None  # Reset

        bridge1 = get_production_bridge()
        bridge2 = get_production_bridge()
        assert bridge1 is bridge2

        # Cleanup
        mod._production_bridge = None
