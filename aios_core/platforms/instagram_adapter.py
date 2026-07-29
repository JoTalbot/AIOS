"""Instagram Platform Adapter — интеграция с Meta Graph API."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from .base import IncomingMessage, PlatformAdapter, SentMessage


class InstagramAdapter(PlatformAdapter):
    """Адаптер для Instagram (Meta Graph API для Business Accounts)."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_account_id = self.config.get("account_id") or os.getenv("INSTAGRAM_ACCOUNT_ID")

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        """Получить новые сообщения из Instagram Direct."""
        # Instagram использует Webhooks для получения сообщений в реальном времени
        # Этот метод используется для initial sync или polling
        
        # TODO: Реальный вызов Graph API
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{self.GRAPH_API_URL}/{self.instagram_account_id}/conversations",
        #         params={
        #             "access_token": self.access_token,
        #             "fields": "messages{id,message,from,created_time}",
        #             "limit": 50
        #         }
        #     )
        #     conversations = response.json()["data"]
        
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict = None) -> SentMessage:
        """Отправить ответ в Instagram Direct."""
        # TODO: Реальный вызов
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.GRAPH_API_URL}/{self.instagram_account_id}/messages",
        #         params={"access_token": self.access_token},
        #         json={
        #             "recipient": {"id": recipient_id},
        #             "message": {"text": text}
        #         }
        #     )
        
        return SentMessage(
            message_id=f"ig_{int(datetime.utcnow().timestamp())}",
            platform="instagram",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # Instagram автоматически помечает как прочитанное при получении
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        # TODO: GET /{user_id}?fields=username,name,profile_pic
        return {"user_id": user_id, "platform": "instagram"}

    async def setup_webhook(self, webhook_url: str, verify_token: str) -> bool:
        """Настроить webhook для получения сообщений в реальном времени."""
        # TODO: POST /{app_id}/subscriptions
        # {
        #     "object": "instagram",
        #     "fields": ["messages"],
        #     "callback_url": webhook_url,
        #     "verify_token": verify_token
        # }
        return True
