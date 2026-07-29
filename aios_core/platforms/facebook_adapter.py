"""Facebook Messenger Platform Adapter (Meta Graph API)."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from .base import IncomingMessage, PlatformAdapter, SentMessage


class FacebookAdapter(PlatformAdapter):
    """Адаптер для Facebook Messenger."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.page_id = self.config.get("page_id") or os.getenv("FACEBOOK_PAGE_ID")

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        # Facebook использует Webhooks (см. aios_core/webhooks/router.py)
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        # TODO: POST /{page_id}/messages (Send API)
        return SentMessage(
            message_id=f"fb_{int(datetime.now(UTC).timestamp())}",
            platform="facebook", recipient_id=recipient_id,
            text=text, timestamp=datetime.now(UTC)
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "platform": "facebook"}
