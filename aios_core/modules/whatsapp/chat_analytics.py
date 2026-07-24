"""WhatsApp/Viber chat analytics — analyze conversation patterns and metrics.

Provides chat analytics for messenger-first platforms:
- Conversation frequency analysis
- Response time tracking
- Sentiment analysis (keyword-based)
- Active chat ranking
- Unread message statistics
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aios_core.modules.olx.storage import OLXStorage


@dataclass
class ChatAnalytics:
    """Analytics summary for a messenger platform."""

    platform: str
    total_outbox_messages: int = 0
    pending_messages: int = 0
    sent_messages: int = 0
    avg_response_time_hours: float | None = None
    active_chats: int = 0
    unread_total: int = 0

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "platform": self.platform,
            "total_outbox_messages": self.total_outbox_messages,
            "pending_messages": self.pending_messages,
            "sent_messages": self.sent_messages,
            "avg_response_time_hours": self.avg_response_time_hours,
            "active_chats": self.active_chats,
            "unread_total": self.unread_total,
        }


class ChatAnalyzer:
    """Analyze chat patterns and metrics for WhatsApp/Viber.

    Uses platform storage to compute analytics from outbox
    and chat history data.
    """

    def __init__(self, storage: OLXStorage, platform: str = "whatsapp") -> None:
        """Initialize ChatAnalyzer.

        Args:
            storage: Platform storage instance.
            platform: Platform name for analytics context.
        """
        self.storage = storage
        self.platform = platform

    def analytics(self) -> ChatAnalytics:
        """Compute full chat analytics summary.

        Returns:
            ChatAnalytics with all computed metrics.
        """
        # Outbox statistics
        outbox = self.storage.outbox_list()
        total = len(outbox)
        pending = sum(1 for m in outbox if m.get("status") == "pending")
        sent = sum(1 for m in outbox if m.get("status") == "sent")

        # Active chats (distinct chat keys)
        active_chats = len({m.get("chat_key") for m in outbox if m.get("chat_key")})

        # Average response time
        response_times: list[float] = []
        for m in outbox:
            created = m.get("created_at")
            sent_at = m.get("sent_at")
            if created and sent_at:
                try:
                    ct = datetime.fromisoformat(created)
                    st = datetime.fromisoformat(sent_at)
                    hours = (st - ct).total_seconds() / 3600
                    if hours > 0:
                        response_times.append(hours)
                except (ValueError, TypeError):
                    pass

        avg_response = None
        if response_times:
            avg_response = sum(response_times) / len(response_times)

        return ChatAnalytics(
            platform=self.platform,
            total_outbox_messages=total,
            pending_messages=pending,
            sent_messages=sent,
            avg_response_time_hours=avg_response,
            active_chats=active_chats,
        )

    def sentiment_summary(self) -> dict[str, object]:
        """Compute sentiment summary from outbox messages.

        Returns:
            Dict with positive/neutral/negative counts.
        """
        positive_kw = [
            "спасибо",
            "добрый",
            "понял",
            "буду",
            "куплю",
            "отлично",
            "подходит",
        ]
        negative_kw = [
            "не",
            "нет",
            "проблема",
            "жаль",
            "слишком",
            "дорого",
            "не подходит",
        ]

        outbox = self.storage.outbox_list()
        positive = 0
        negative = 0
        neutral = 0

        for m in outbox:
            text = (m.get("text") or "").lower()
            has_pos = any(k in text for k in positive_kw)
            has_neg = any(k in text for k in negative_kw)
            if has_pos and not has_neg:
                positive += 1
            elif has_neg and not has_pos:
                negative += 1
            else:
                neutral += 1

        return {
            "platform": self.platform,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "total": len(outbox),
        }
