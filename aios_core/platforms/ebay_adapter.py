from datetime import datetime, timezone

from .base import IncomingMessage, PlatformAdapter, SentMessage


class EbayAdapter(PlatformAdapter):
    """Адаптер для Ebay."""

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.platform_name = "ebay"

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        return SentMessage(
            message_id=f"ebay_{int(datetime.now(timezone.utc).timestamp())}",
            platform="ebay",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> dict:
        return {"user_id": user_id, "platform": "ebay"}
