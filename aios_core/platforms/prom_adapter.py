"""Prom.ua Platform Adapter."""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class PromAdapter(PlatformAdapter):
    """Адаптер для Prom.ua."""
    
    API_URL = "https://my.prom.ua/api/v1"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.api_key = self.config.get("api_key") or os.getenv("PROM_API_KEY")
        self.client_id = self.config.get("client_id") or os.getenv("PROM_CLIENT_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # TODO: GET /chat_messages
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /chat_messages
        return SentMessage(
            message_id=f"prom_{int(datetime.utcnow().timestamp())}",
            platform="prom", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": "prom"}
