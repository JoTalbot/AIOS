"""OLX Platform Adapter — интеграция с OLX API."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone, timedelta
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
        self._token_expires: datetime | None = None

    async def _ensure_token(self) -> None:
        """Обновить OAuth2 токен если нужно."""
        if self.access_token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return

        # Реальный OAuth2 flow с POST запросом для получения токена
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "read write",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        """Получить новые сообщения из OLX threads."""
        await self._ensure_token()

        # Заменяем GET на POST с необходимыми параметрами и токеном
        params = {}
        if since:
            params["last_id"] = int(since.timestamp())

        response_json = await self._make_request(
            "POST",
            f"{self.BASE_URL}/threads",
            json_data={"params": params, "access_token": self.access_token},
        )
        threads = response_json.get("data", [])

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

        # Заменяем GET на POST с необходимыми параметрами и токеном
        response_json = await self._make_request(
            "POST",
            f"{self.BASE_URL}/threads/{recipient_id}/messages",
            json_data={"text": text, "access_token": self.access_token},
        )

        return SentMessage(
            message_id=f"olx_{int(datetime.now(timezone.utc).timestamp())}",
            platform="olx",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.now(timezone.utc),
        )

    async def mark_as_read(self, message_id: str) -> bool:
        """Отметить сообщение как прочитанное."""
        await self._ensure_token()

        # Заменяем GET на POST с необходимыми параметрами и токеном
        try:
            await self._make_request(
                "POST",
                f"{self.BASE_URL}/threads/{message_id}/read",
                json_data={"access_token": self.access_token},
            )
            return True
        except Exception:
            return False

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Получить информацию о пользователе."""
        await self._ensure_token()

        # Заменяем GET на POST с необходимыми параметрами и токеном
        response_json = await self._make_request(
            "POST",
            f"{self.BASE_URL}/users/{user_id}",
            json_data={"access_token": self.access_token},
        )
        return response_json

    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        """Выполнить HTTP запрос с авторизацией и обработкой ошибок."""
        import httpx

        headers = {
            "Authorization": f"Bearer {self.access_token}" if self.access_token else "",
            "Content-Type": "application/json",
        }

        try:
            response = await self._make_request_with_retry(
                method, url, headers=headers, params=params, json_data=json_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Request failed with status code {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            raise Exception(f"Failed to make request: {e}") from e

    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        json_data: dict | None = None,
        max_retries: int = 3,
    ) -> Any:
        """Выполнить HTTP запрос с повторными попытками."""
        import httpx

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=headers, params=params, json=json_data)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    if 200 <= response.status_code < 300:
                        return response
                    else:
                        response.raise_for_status()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(1)