"""WhatsApp Platform Adapter (Meta Cloud API)."""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class WhatsAppAdapter(PlatformAdapter):
    """Адаптер для WhatsApp Business (Meta Cloud API)."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = self.config.get("phone_number_id") or os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # WhatsApp использует Webhooks
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /{phone_number_id}/messages
        return SentMessage(
            message_id=f"wa_{int(datetime.utcnow().timestamp())}",
            platform="whatsapp", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # TODO: POST /{phone_number_id}/messages с status=mark_as_read
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": "whatsapp"}
