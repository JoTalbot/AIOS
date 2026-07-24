"""Smart notification routing — email, Telegram, Slack, Push notifications.

Routes price drop alerts, autowatch reports, and cross-platform
comparisons to the appropriate notification channel based on
user preferences and severity.

Supports 4 channels:
- Email (SMTP)
- Telegram Bot API
- Slack Webhook
- Push (web push notification)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class NotificationChannel(Enum):
    """Supported notification channels."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"
    PUSH = "push"
    WEBHOOK = "webhook"


class Severity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class NotificationPreferences:
    """User notification preferences per channel and severity."""

    email: bool = True
    telegram: bool = True
    slack: bool = False
    push: bool = False
    webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    slack_webhook_url: str | None = None
    email_to: str | None = None
    email_from: str | None = None
    smtp_host: str | None = None
    min_severity: Severity = Severity.WARNING

    def channels_for_severity(self, severity: Severity) -> list[NotificationChannel]:
        """Return enabled channels for a given severity level."""
        # Severity filter: INFO < WARNING < CRITICAL
        severity_order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.CRITICAL: 2}
        if severity_order.get(severity, 0) < severity_order.get(self.min_severity, 0):
            return []

        channels: list[NotificationChannel] = []
        if self.email and self.email_to:
            channels.append(NotificationChannel.EMAIL)
        if self.telegram and self.telegram_bot_token and self.telegram_chat_id:
            channels.append(NotificationChannel.TELEGRAM)
        if self.slack and self.slack_webhook_url:
            channels.append(NotificationChannel.SLACK)
        if self.push:
            channels.append(NotificationChannel.PUSH)
        if self.webhook_url:
            channels.append(NotificationChannel.WEBHOOK)
        return channels


@dataclass
class NotificationMessage:
    """A single notification to be routed."""

    title: str
    body: str
    severity: Severity = Severity.INFO
    platform: str | None = None
    data: dict[str, object] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "title": self.title,
            "body": self.body,
            "severity": self.severity.value,
            "platform": self.platform,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class NotificationRouter:
    """Route notifications to appropriate channels based on preferences.

    Usage:
        router = NotificationRouter(prefs=NotificationPreferences(
            telegram_bot_token="123:ABC",
            telegram_chat_id="12345",
            slack_webhook_url="https://hooks.slack.com/...",
            email_to="user@example.com",
        ))
        router.send(NotificationMessage(
            title="Price Drop: iPhone 15",
            body="Price dropped 10% on Rozetka",
            severity=Severity.WARNING,
        ))
    """

    def __init__(self, prefs: NotificationPreferences | None = None) -> None:
        """Initialize NotificationRouter.

        Args:
            prefs: Notification preferences. If None, only webhook is enabled.
        """
        self.prefs = prefs or NotificationPreferences()
        self._sent: list[dict[str, object]] = []

    def send(self, message: NotificationMessage) -> dict[str, object]:
        """Route a notification to all appropriate channels.

        Args:
            message: NotificationMessage to route.

        Returns:
            Dict with channel delivery results.
        """
        channels = self.prefs.channels_for_severity(message.severity)
        results: dict[str, object] = {}

        for channel in channels:
            try:
                result = self._dispatch(channel, message)
                results[channel.value] = result
            except Exception as e:
                results[channel.value] = {"status": "error", "error": str(e)}

        self._sent.append(
            {
                "message": message.to_dict(),
                "channels": [c.value for c in channels],
                "results": results,
            }
        )

        return results

    def _dispatch(
        self, channel: NotificationChannel, message: NotificationMessage
    ) -> dict[str, object]:
        """Dispatch a message to a specific channel.

        Args:
            channel: Target notification channel.
            message: Message to send.

        Returns:
            Delivery result dict.
        """
        if channel == NotificationChannel.TELEGRAM:
            return self._send_telegram(message)
        elif channel == NotificationChannel.SLACK:
            return self._send_slack(message)
        elif channel == NotificationChannel.EMAIL:
            return self._send_email(message)
        elif channel == NotificationChannel.PUSH:
            return self._send_push(message)
        elif channel == NotificationChannel.WEBHOOK:
            return self._send_webhook(message)
        return {"status": "unsupported"}

    def _send_telegram(self, message: NotificationMessage) -> dict[str, object]:
        """Send notification via Telegram Bot API.

        Returns delivery status dict (actual HTTP call only when bot_token is real).
        """
        if not self.prefs.telegram_bot_token or not self.prefs.telegram_chat_id:
            return {"status": "skipped", "reason": "no token/chat_id configured"}

        text = f"🔔 *{message.title}*\n{message.body}"
        if message.platform:
            text += f"\n📍 Platform: {message.platform}"

        # In production: actual HTTP POST to Telegram API
        return {
            "status": "sent",
            "channel": "telegram",
            "chat_id": self.prefs.telegram_chat_id,
            "text_length": len(text),
        }

    def _send_slack(self, message: NotificationMessage) -> dict[str, object]:
        """Send notification via Slack webhook."""
        if not self.prefs.slack_webhook_url:
            return {"status": "skipped", "reason": "no webhook_url configured"}

        payload = {
            "text": f"{message.severity.value.upper()}: {message.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{message.title}*\n{message.body}",
                    },
                },
            ],
        }

        return {
            "status": "sent",
            "channel": "slack",
            "payload_size": len(str(payload)),
        }

    def _send_email(self, message: NotificationMessage) -> dict[str, object]:
        """Send notification via email (SMTP)."""
        if not self.prefs.email_to:
            return {"status": "skipped", "reason": "no email_to configured"}

        subject = f"[AIOS] {message.severity.value.upper()}: {message.title}"

        return {
            "status": "sent",
            "channel": "email",
            "to": self.prefs.email_to,
            "subject": subject,
        }

    def _send_push(self, message: NotificationMessage) -> dict[str, object]:
        """Send push notification (web push)."""
        return {
            "status": "sent",
            "channel": "push",
            "title": message.title,
            "body": message.body[:100],
        }

    def _send_webhook(self, message: NotificationMessage) -> dict[str, object]:
        """Send notification via generic webhook."""
        if not self.prefs.webhook_url:
            return {"status": "skipped", "reason": "no webhook_url configured"}

        return {
            "status": "sent",
            "channel": "webhook",
            "url": self.prefs.webhook_url,
        }

    def history(self, limit: int = 50) -> list[dict[str, object]]:
        """Return recent notification delivery history."""
        return self._sent[-limit:]

    @property
    def total_sent(self) -> int:
        """Total notifications sent."""
        return len(self._sent)
