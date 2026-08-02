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
        # TODO: POST /chat_messages
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        # TODO: POST /chat_messages
        return SentMessage(
            message_id=f"prom_{int(datetime.now(timezone.utc).timestamp())}",
            platform="prom",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # TODO: POST /chat_messages
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        # TODO: POST /chat_messages
        return {"user_id": user_id, "platform": "prom"}