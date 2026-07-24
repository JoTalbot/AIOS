"""Viber chat analytics — inherits WhatsApp ChatAnalyzer for Viber platform."""

from aios_core.modules.whatsapp.chat_analytics import ChatAnalyzer


class ViberChatAnalyzer(ChatAnalyzer):
    """Chat analytics for Viber — same interface as WhatsApp."""

    def __init__(self, storage, platform: str = "viber") -> None:
        """Initialize ViberChatAnalyzer."""
        super().__init__(storage, platform=platform)
