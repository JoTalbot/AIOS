"""OLX Platform Adapter — интеграция с OLX API."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from .base import IncomingMessage, PlatformAdapter, SentMessage


class OLXAdapter(PlatformAdapter):
    """Адаптер для OLX.ua (использует OLX API v2)."""

    BASE_URL = "https://www.olx.ua/api/v1"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.client_id = self.config.get("client_id") or os.getenv("OLX_CLIENT_ID")
        self.client_secret = self.config.get("client_secret") or os.getenv("OLX_CLIENT_SECRET")
        self.access_token = self.config.get("access_token") or os.getenv("OLX_ACCESS_TOKEN")
        self._token_expires = None

    async def _ensure_token(self):
        """Обновить OAuth2 токен если нужно."""
        if self.access_token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return

        # TODO: Реальный OAuth2 flow
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.BASE_URL}/oauth/token",
        #         data={
        #             "grant_type": "client_credentials",
        #             "client_id": self.client_id,
        #             "client_secret": self.client_secret,
        #             "scope": "read write"
        #         }
        #     )
        #     data = response.json()
        #     self.access_token = data["access_token"]
        #     self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        """Получить новые сообщения из OLX threads."""
        await self._ensure_token()

        # TODO: Реальный вызов OLX API
        response = await self._make_request(
            "GET",
            f"{self.BASE_URL}/threads",
            params={"last_id": since.timestamp() if since else None}
        )
        threads = response.json()["data"]

        return [
            IncomingMessage(
                message_id=thread["id"],
                platform="olx",
                recipient_id=thread["user"]["id"],
                text=thread["text"],
                timestamp=datetime.fromtimestamp(thread["created_at"], timezone.utc),
            )
            for thread in threads
        ]

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        """Отправить ответ в OLX thread."""
        await self._ensure_token()

        # TODO: Реальный вызов
        response = await self._make_request(
            "POST",
            f"{self.BASE_URL}/threads/{recipient_id}/messages",
            json={"text": text}
        )

        return SentMessage(
            message_id=f"olx_{int(datetime.now(timezone.utc).timestamp())}",
            platform="olx",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        await self._ensure_token()
        # TODO: PUT /threads/{thread_id}/read
        return True

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        await self._ensure_token()
        # TODO: GET /users/{user_id}
        response = await self._make_request("GET", f"{self.BASE_URL}/users/{user_id}")
        return {"user_id": user_id, "platform": "olx"}

    async def _make_request(self, method: str, url: str, params: dict | None = None, json_data: dict | None = None):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._make_request_with_retry(method, url, headers=headers, params=params, json_data=json_data)
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to make request: {e}")

    async def _make_request_with_retry(self, method: str, url: str, headers: dict | None = None, params: dict | None = None, json_data: dict | None = None, max_retries=3):
        for i in range(max_retries):
            try:
                if method == "GET":
                    response = await self._make_get_request(url, headers=headers, params=params)
                elif method == "POST":
                    response = await self._make_post_request(url, headers=headers, json_data=json_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code >= 200 and response.status_code < 300:
                    return response
                else:
                    raise Exception(f"Request failed with status code {response.status_code}")
            except Exception as e:
                if i == max_retries - 1:
                    raise e
                await asyncio.sleep(1)