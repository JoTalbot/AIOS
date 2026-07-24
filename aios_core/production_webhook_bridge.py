"""Production Autopilot Webhook Integration

Sends webhook notifications for critical production events:
- Ban detected
- Low success rate
- Device offline
- Compliance blocked
- Backup completed/failed
- Daily report summary
"""

from typing import Any, Dict, List, Optional

from .webhook_manager import WebhookEvent, WebhookManager


class ProductionWebhookBridge:
    """Bridges ProductionAutopilot events to WebhookManager."""

    def __init__(self, webhook_manager: Optional[WebhookManager] = None):
        """Initialize ProductionWebhookBridge."""
        self.webhook = webhook_manager or WebhookManager()
        self.enabled = True

    def on_ban_detected(self, profile: str, reason: str, details: Optional[Dict] = None) -> None:
        """Notify when a ban is detected."""
        if not self.enabled:
            return
        data = {
            "profile": profile,
            "reason": reason,
            "source": "production_autopilot",
        }
        if details:
            data.update(details)
        return self.webhook.notify(
            event=WebhookEvent.BAN_DETECTED,
            data=data,
            source="production_autopilot",
            severity="critical",
        )

    def on_low_success_rate(self, profile: str, rate: float, threshold: float = 0.8) -> None:
        """Notify when success rate drops below threshold."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.LOW_SUCCESS_RATE,
            data={
                "profile": profile,
                "success_rate": round(rate, 4),
                "threshold": threshold,
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="warning",
        )

    def on_device_offline(self, device_serial: str, profile: str) -> None:
        """Notify when a device goes offline."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.DEVICE_OFFLINE,
            data={
                "device_serial": device_serial,
                "profile": profile,
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="warning",
        )

    def on_compliance_blocked(self, profile: str, action: str, reason: str) -> None:
        """Notify when compliance guard blocks an action."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.COMPLIANCE_BLOCKED,
            data={
                "profile": profile,
                "action": action,
                "reason": reason,
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="warning",
        )

    def on_backup_completed(self, backup_id: str, size_mb: float) -> None:
        """Notify when backup completes."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.BACKUP_COMPLETED,
            data={
                "backup_id": backup_id,
                "size_mb": round(size_mb, 2),
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="info",
        )

    def on_backup_failed(self, error: str) -> None:
        """Notify when backup fails."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.BACKUP_FAILED,
            data={
                "error": error,
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="critical",
        )

    def on_daily_report(self, report: dict[str, Any]) -> None:
        """Send daily summary notification."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event="daily_report",
            data={
                "date": report.get("date", "unknown"),
                "total_cycles": report.get("total_cycles", 0),
                "total_actions": report.get("total_actions", 0),
                "avg_success_rate": report.get("avg_success_rate", 0),
                "bans": report.get("bans", 0),
                "drifts": report.get("drifts", 0),
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="info",
        )

    def on_simulation_complete(self, summary: dict[str, Any]) -> None:
        """Send simulation completion notification."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event="simulation_complete",
            data={
                "days": summary.get("simulation", {}).get("days", 14),
                "profiles": summary.get("simulation", {}).get("profiles", 0),
                "total_cycles": summary.get("simulation", {}).get("total_cycles", 0),
                "avg_success_rate": summary.get("simulation", {}).get("avg_success_rate", 0),
                "bans": summary.get("simulation", {}).get("bans", 0),
                "ban_free": summary.get("simulation", {}).get("ban_free", False),
                "ga_criteria_met": summary.get("simulation", {}).get("ga_criteria_met", False),
                "source": "production_autopilot",
            },
            source="production_autopilot",
            severity="info",
        )

    def on_key_rotated(self, subject: str, old_key_prefix: str, new_key_prefix: str) -> None:
        """Notify when an API key is rotated."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.KEY_ROTATED,
            data={
                "subject": subject,
                "old_key_prefix": old_key_prefix,
                "new_key_prefix": new_key_prefix,
                "source": "secret_manager",
            },
            source="secret_manager",
            severity="info",
        )

    def on_key_revoked(self, subject: str, key_prefix: str, reason: str) -> None:
        """Notify when an API key is revoked."""
        if not self.enabled:
            return
        return self.webhook.notify(
            event=WebhookEvent.KEY_REVOKED,
            data={
                "subject": subject,
                "key_prefix": key_prefix,
                "reason": reason,
                "source": "secret_manager",
            },
            source="secret_manager",
            severity="warning",
        )


# Singleton for convenience
_production_bridge: Optional[ProductionWebhookBridge] = None


def get_production_bridge(
    webhook_manager: Optional[WebhookManager] = None,
) -> ProductionWebhookBridge:
    """Get or create the singleton production webhook bridge."""
    global _production_bridge
    if _production_bridge is None:
        _production_bridge = ProductionWebhookBridge(webhook_manager)
    return _production_bridge
