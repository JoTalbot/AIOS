"""Facebook Messenger Platform Adapter (Meta Graph API)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
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
        # POST /{page_id}/messages (Send API)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
        }
        async with self.session.post(f"{self.GRAPH_API_URL}/{self.page_id}/messages", headers=headers, json=payload) as response:
            if response.status == 200:
                return SentMessage(
                    message_id=f"fb_{int(datetime.now(timezone.utc).timestamp())}",
                    platform="facebook",
                    recipient_id=recipient_id,
                    text=text,
                    timestamp=datetime.now(timezone.utc),
                )
            else:
                raise Exception(f"Failed to send message: {response.status} - {await response.text()}")

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        # GET /{user_id}/info (User API)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        async with self.session.get(f"{self.GRAPH_API_URL}/{user_id}/info", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get user info: {response.status} - {await response.text()}")

# Unit tests
import unittest

class TestFacebookAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = FacebookAdapter()

    async def test_send_message(self):
        recipient_id = "1234567890"
        text = "Hello, world!"
        message = await self.adapter.send_message(recipient_id, text)
        self.assertEqual(message.message_id, f"fb_{int(datetime.now(timezone.utc).timestamp())}")
        self.assertEqual(message.platform, "facebook")
        self.assertEqual(message.recipient_id, recipient_id)
        self.assertEqual(message.text, text)
        self.assertIsNotNone(message.timestamp)

    async def test_mark_as_read(self):
        message_id = "1234567890"
        result = await self.adapter.mark_as_read(message_id)
        self.assertTrue(result)

    async def test_get_user_info(self):
        user_id = "1234567890"
        info = await self.adapter.get_user_info(user_id)
        self.assertEqual(info["user_id"], user_id)
        self.assertEqual(info["platform"], "facebook")

if __name__ == "__main__":
    unittest.main()