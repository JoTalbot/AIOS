
from typing import List, Dict, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class TiktokShopAdapter(PlatformAdapter):
    """Адаптер для Tiktok Shop."""
    
    def __init__(self, config: Dict = None):
        super().__init__(config or {})
        self.platform_name = "tiktok_shop"
    
    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        return []
    
    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        return SentMessage(
            message_id=f"tiktok_shop_{int(datetime.utcnow().timestamp())}",
            platform="tiktok_shop",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.utcnow()
        )
    
    async def mark_as_read(self, message_id: str) -> bool:
        return True
    
    async def get_user_info(self, user_id: str) -> Dict:
        return {"user_id": user_id, "platform": "tiktok_shop"}
