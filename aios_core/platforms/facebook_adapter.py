"""Facebook Messenger Platform Adapter (Meta Graph API)."""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class FacebookAdapter(PlatformAdapter):
    """Адаптер для Facebook Messenger."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.page_id = self.config.get("page_id") or os.getenv("FACEBOOK_PAGE_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # Facebook использует Webhooks (см. aios_core/webhooks/router.py)
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /{page_id}/messages (Send API)
        return SentMessage(
            message_id=f"fb_{int(datetime.utcnow().timestamp())}",
            platform="facebook", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": "facebook"}
