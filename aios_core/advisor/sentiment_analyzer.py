"""Sentiment Analyzer — определение тональности и эскалация."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SentimentResult:
    sentiment: str  # 'positive', 'neutral', 'negative'
    confidence: float
    requires_escalation: bool
    reason: str


class SentimentAnalyzer:
    def __init__(self):
        self.negative_markers = {
            "uk": ["обман", "шахрай", "повернення", "скаррга", "не працює"],
            "ru": ["обман", "мошенник", "возврат", "жалоба", "не работает"],
            "en": ["scam", "fraud", "refund", "complaint", "broken"],
        }

    def analyze(self, message: str, language: str = "uk") -> SentimentResult:
        msg = message.lower()
        markers = self.negative_markers.get(language, self.negative_markers["uk"])

        matches = sum(1 for m in markers if m in msg)

        if matches >= 2:
            return SentimentResult(
                sentiment="negative",
                confidence=0.9,
                requires_escalation=True,
                reason=f"Найдено {matches} негативных маркеров",
            )
        elif matches == 1:
            return SentimentResult(
                sentiment="negative", confidence=0.6, requires_escalation=False, reason="Найден 1 негативный маркер"
            )

        return SentimentResult(
            sentiment="neutral", confidence=0.7, requires_escalation=False, reason="Нейтральная тональность"
        )
