"""Prom.ua Platform Adapter."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from .base import IncomingMessage, PlatformAdapter, SentMessage


class PromAdapter(PlatformAdapter):
    """Адаптер для Prom.ua."""

    API_URL = "https://my.prom.ua/api/v1"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.api_key = self.config.get("api_key") or os.getenv("PROM_API_KEY")
        self.client_id = self.config.get("client_id") or os.getenv("PROM_CLIENT_ID")

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        # POST /chat_messages
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        # POST /chat_messages
        try:
            response = await self._make_request("POST", f"{self.API_URL}/chat_messages", json={"recipient_id": recipient_id, "text": text})
            return SentMessage(
                message_id=response.json().get("message_id"),
                platform="prom",
                recipient_id=recipient_id,
                text=text,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            raise RuntimeError(f"Failed to send message: {e}")

    async def mark_as_read(self, message_id: str) -> bool:
        # POST /chat_messages
        try:
            response = await self._make_request("POST", f"{self.API_URL}/chat_messages/{message_id}", json={"read": True})
            return response.status_code == 200
        except Exception as e:
            raise RuntimeError(f"Failed to mark message as read: {e}")

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        # POST /chat_messages
        try:
            response = await self._make_request("POST", f"{self.API_URL}/chat_messages/{user_id}", json={"get_user_info": True})
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get user info: {e}")

    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Client-ID": self.client_id,
        }
        response = await self._send_request(method, url, headers=headers, **kwargs)
        return response.json()

    async def _send_request(self, method: str, url: str, headers: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"HTTP error {response.status}")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to make request: {e}")