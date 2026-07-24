"""AIOS OLX Android Agent — alert notifications (webhooks, Telegram-ready)."""

from __future__ import annotations

import json
import urllib.request


class WebhookNotifier:
    """Posts alert events as JSON to a webhook URL.

    Compatible with Slack/Discord-style incoming webhooks and with the
    Telegram Bot API ``sendMessage`` endpoint (pass a ready URL):
    ``https://api.telegram.org/bot<TOKEN>/sendMessage`` with payloads of the
    form ``{"chat_id": ..., "text": ...}``.
    """

    def __init__(self, url: str | None = None, poster=None, chat_id: str | None = None):
        """Initialize WebhookNotifier."""
        self.url = url
        self.chat_id = chat_id
        self._poster = poster or self._urllib_post

    def send(self, event: str, data: dict[str, object]) -> bool:
        """Send one event. Returns True on HTTP 2xx. Silent no-op without URL."""
        if not self.url:
            return False
        payload = {"event": event, "data": data}
        if "telegram.org" in self.url and self.chat_id:
            payload = {
                "chat_id": self.chat_id,
                "text": f"[{event}] " + json.dumps(data, ensure_ascii=False),
            }
        return bool(self._poster(self.url, payload))

    @staticmethod
    def _urllib_post(url: str, payload: dict[str, object]) -> bool:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300


def collect_price_drop_alerts(
    tracker, query: str | None = None
) -> list[dict[str, object]]:
    """Turn tracker price drops into notifier-ready alert payloads."""
    alerts: list[dict[str, object]] = []
    for drop in tracker.price_drops(query=query):
        alerts.append(
            {
                "type": "price_drop",
                "title": drop.title,
                "first_price": drop.first_price,
                "last_price": drop.last_price,
                "change_pct": drop.change_pct,
                "city": drop.city,
                "url": drop.url,
            }
        )
    return alerts


def notify_price_drops(
    tracker, notifier: WebhookNotifier, query: str | None = None
) -> dict[str, object]:
    """Send one webhook event per new price drop. Returns a summary."""
    alerts = collect_price_drop_alerts(tracker, query=query)
    sent = 0
    for alert in alerts:
        if notifier.send("olx_price_drop", alert):
            sent += 1
    return {"alerts": len(alerts), "sent": sent}


def notify_stagnant(
    stagnant_items: list[dict[str, object]], notifier: WebhookNotifier
) -> dict[str, object]:
    """Notify about own stagnant listings (repost/improve candidates)."""
    sent = 0
    for item in stagnant_items:
        alert = dict(item)
        alert["type"] = "own_ad_stagnant"
        if notifier.send("olx_own_ad_stagnant", alert):
            sent += 1
    return {"alerts": len(stagnant_items), "sent": sent}
