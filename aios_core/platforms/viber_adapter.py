"""Viber Platform Adapter."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from .base import IncomingMessage, PlatformAdapter, SentMessage


class ViberAdapter(PlatformAdapter):
    """Адаптер для Viber Public Accounts."""

    API_URL = "https://chatapi.viber.com/pa"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.auth_token = self.config.get("auth_token") or os.getenv("VIBER_AUTH_TOKEN")

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        # Viber uses Webhooks
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        # Реальная отправка в Viber идёт через desktop-автоматизацию
        # (viber_control.py); Cloud API здесь не используется — возвращаем
        # подтверждение намерения, как и прочие scaffold-адаптеры.
        return SentMessage(
            message_id=f"viber_{int(datetime.now(timezone.utc).timestamp())}",
            platform="viber",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        # POST /get_user_details
        url = f"{self.API_URL}/get_user_details"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
        }
        data = {
            "user_id": user_id,
        }
        async with self.session.post(url, json=data) as response:
            if response.status == 200:
                return {"user_id": user_id, "platform": "viber"}
            else:
                raise Exception(f"Failed to get user info: {response.status}")

    async def set_webhook(self, url: str) -> bool:
        """Настроить webhook для Viber."""
        # POST /set_webhook
        url = f"{self.API_URL}/set_webhook"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
        }
        data = {
            "url": url,
        }
        async with self.session.post(url, json=data) as response:
            if response.status == 200:
                return True
            else:
                raise Exception(f"Failed to set webhook: {response.status}")