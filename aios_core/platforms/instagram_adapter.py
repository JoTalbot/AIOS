"""Instagram Platform Adapter — интеграция с Meta Graph API."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from .base import IncomingMessage, PlatformAdapter, SentMessage


class InstagramAdapter(PlatformAdapter):
    """Адаптер для Instagram (Meta Graph API для Business Accounts)."""

    GRAPH_API_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_account_id = self.config.get("account_id") or os.getenv("INSTAGRAM_ACCOUNT_ID")

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        """Получить новые сообщения из Instagram Direct."""
        # Instagram использует Webhooks для получения сообщений в реальном времени
        # Этот метод используется для initial sync или polling

        try:
            response = await self._make_request(
                method="GET",
                url=f"{self.GRAPH_API_URL}/{self.instagram_account_id}/conversations",
                params={
                    "access_token": self.access_token,
                    "fields": "messages{id,message,from,created_time}",
                    "limit": 50
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to fetch messages: {e}")

        conversations = response.json()["data"]
        return [self._convert_to_incoming_message(conversation) for conversation in conversations]

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        """Отправить ответ в Instagram Direct."""
        try:
            response = await self._make_request(
                method="POST",
                url=f"{self.GRAPH_API_URL}/{self.instagram_account_id}/messages",
                params={"access_token": self.access_token},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": text}
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to send message: {e}")

        return SentMessage(
            message_id=f"ig_{int(datetime.now(timezone.utc).timestamp())}",
            platform="instagram",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # Instagram автоматически помечает как прочитанное при получении
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        # TODO: GET /{user_id}?fields=username,name,profile_pic
        try:
            response = await self._make_request(
                method="GET",
                url=f"{self.GRAPH_API_URL}/{user_id}",
                params={"access_token": self.access_token}
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get user info: {e}")

        return {"user_id": user_id, "platform": "instagram"}

    async def setup_webhook(self, webhook_url: str, verify_token: str) -> bool:
        """Настроить webhook для получения сообщений в реальном времени."""
        try:
            response = await self._make_request(
                method="POST",
                url=f"{self.GRAPH_API_URL}/{app_id}/subscriptions",
                params={"object": "instagram", "fields": ["messages"], "callback_url": webhook_url, "verify_token": verify_token}
            )
        except Exception as e:
            raise RuntimeError(f"Failed to setup webhook: {e}")

    async def _make_request(self, method: str, url: str, params: dict[str, Any] = {}, json_data: dict | None = None) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error occurred: {e}")