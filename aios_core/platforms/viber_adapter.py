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
        # Viber использует Webhooks
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        # TODO: POST /send_message
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
        # TODO: POST /get_user_details
        return {"user_id": user_id, "platform": "viber"}

    async def set_webhook(self, url: str) -> bool:
        """Настроить webhook для Viber."""
        # TODO: POST /set_webhook
        return True
