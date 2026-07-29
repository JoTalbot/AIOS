
from datetime import UTC, datetime

from .base import IncomingMessage, PlatformAdapter, SentMessage


class TiktokAdapter(PlatformAdapter):
    """Адаптер для Tiktok."""
    
    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.platform_name = "tiktok"
    
    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        return []
    
    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        return SentMessage(
            message_id=f"tiktok_{int(datetime.now(UTC).timestamp())}",
            platform="tiktok",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(UTC)
        )
    
    async def mark_as_read(self, message_id: str) -> bool:
        return True
    
    async def get_user_info(self, user_id: str) -> dict:
        return {"user_id": user_id, "platform": "tiktok"}
