"""WhatsApp Platform Adapter (Meta Cloud API)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from .base import IncomingMessage, PlatformAdapter, SentMessage


class WhatsAppAdapter(PlatformAdapter):
    """Адаптер для WhatsApp Business (Meta Cloud API)."""

    GRAPH_API_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = self.config.get("phone_number_id") or os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        # WhatsApp использует Webhooks
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        # TODO: POST /{phone_number_id}/messages
        return SentMessage(
            message_id=f"wa_{int(datetime.now(UTC).timestamp())}",
            platform="whatsapp",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(UTC),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # TODO: POST /{phone_number_id}/messages с status=mark_as_read
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "platform": "whatsapp"}
