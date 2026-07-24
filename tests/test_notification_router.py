"""Tests for notification router — smart routing to email/Telegram/Slack/Push."""

from __future__ import annotations

from aios_core.notification_router import (
    NotificationRouter, NotificationMessage, NotificationPreferences,
    NotificationChannel, Severity,
)


def test_notification_channel_enum():
    """All NotificationChannel values are present."""
    assert NotificationChannel.EMAIL.value == "email"
    assert NotificationChannel.TELEGRAM.value == "telegram"
    assert NotificationChannel.SLACK.value == "slack"
    assert NotificationChannel.PUSH.value == "push"
    assert NotificationChannel.WEBHOOK.value == "webhook"


def test_severity_enum():
    """Severity enum values are distinct strings."""
    assert Severity.INFO.value == "info"
    assert Severity.WARNING.value == "warning"
    assert Severity.CRITICAL.value == "critical"


def test_notification_preferences_defaults():
    """Default preferences enable email and telegram."""
    prefs = NotificationPreferences()
    assert prefs.email is True
    assert prefs.telegram is True
    assert prefs.slack is False


def test_notification_preferences_channels():
    """channels_for_severity returns correct channels."""
    prefs = NotificationPreferences(
        telegram_bot_token="123:ABC",
        telegram_chat_id="12345",
        slack=True,
        slack_webhook_url="https://hooks.slack.com/...",
        email_to="user@example.com",
        min_severity=Severity.WARNING,
    )
    channels = prefs.channels_for_severity(Severity.WARNING)
    assert NotificationChannel.TELEGRAM in channels
    assert NotificationChannel.EMAIL in channels
    assert NotificationChannel.SLACK in channels


def test_notification_preferences_min_severity():
    """min_severity filters out lower severity."""
    prefs = NotificationPreferences(
        min_severity=Severity.CRITICAL,
        telegram_bot_token="123:ABC",
        telegram_chat_id="12345",
    )
    channels = prefs.channels_for_severity(Severity.INFO)
    assert len(channels) == 0


def test_notification_message_to_dict():
    """NotificationMessage serializes to dict."""
    msg = NotificationMessage(
        title="Price Drop",
        body="iPhone dropped 10%",
        severity=Severity.WARNING,
        platform="rozetka",
    )
    d = msg.to_dict()
    assert d["title"] == "Price Drop"
    assert d["severity"] == "warning"
    assert d["platform"] == "rozetka"


def test_notification_router_send_telegram():
    """Router sends Telegram notification."""
    prefs = NotificationPreferences(
        telegram_bot_token="123:ABC",
        telegram_chat_id="12345",
        min_severity=Severity.WARNING,
    )
    router = NotificationRouter(prefs=prefs)
    msg = NotificationMessage(title="Alert", body="Test", severity=Severity.WARNING)
    results = router.send(msg)
    assert "telegram" in results
    assert results["telegram"]["status"] == "sent"


def test_notification_router_send_slack():
    """Router sends Slack notification."""
    prefs = NotificationPreferences(
        slack=True,
        slack_webhook_url="https://hooks.slack.com/test",
        min_severity=Severity.WARNING,
    )
    router = NotificationRouter(prefs=prefs)
    msg = NotificationMessage(title="Alert", body="Test", severity=Severity.WARNING)
    results = router.send(msg)
    assert "slack" in results
    assert results["slack"]["status"] == "sent"


def test_notification_router_send_email():
    """Router sends email notification."""
    prefs = NotificationPreferences(email_to="user@example.com", min_severity=Severity.WARNING)
    router = NotificationRouter(prefs=prefs)
    msg = NotificationMessage(title="Alert", body="Test", severity=Severity.WARNING)
    results = router.send(msg)
    assert "email" in results


def test_notification_router_history():
    """Router tracks sent notification history."""
    router = NotificationRouter(prefs=NotificationPreferences(
        telegram_bot_token="123:ABC", telegram_chat_id="12345",
        min_severity=Severity.WARNING,
    ))
    router.send(NotificationMessage(title="Msg1", body="Test", severity=Severity.WARNING))
    router.send(NotificationMessage(title="Msg2", body="Test2", severity=Severity.CRITICAL))

    assert router.total_sent == 2
    history = router.history()
    assert len(history) >= 2


def test_notification_router_no_channels():
    """Router with no configured channels returns empty results."""
    prefs = NotificationPreferences(
        email=False, telegram=False, slack=False, push=False, webhook_url=None,
        min_severity=Severity.INFO,
    )
    router = NotificationRouter(prefs=prefs)
    msg = NotificationMessage(title="Alert", body="Test", severity=Severity.WARNING)
    results = router.send(msg)
    assert len(results) == 0
