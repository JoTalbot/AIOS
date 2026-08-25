"""Клиент OpenHands Cloud API (V1) для OpenHands-контура AIOS.

Отдельный адаптер: бизнес-логика AIOS (оркестратор, гейты) сюда не поднимается.
Auth: ``OPENHANDS_CLOUD_API_KEY`` (предпочтительно) или ``OPENHANDS_API_KEY``.
Эндпоинты — V1 app server ``/api/v1/...`` (см. docs.openhands.dev, cloud-api).
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .errors import (
    OpenHandsAPIError,
    OpenHandsAuthError,
    OpenHandsStartError,
    OpenHandsTimeoutError,
)

DEFAULT_BASE_URL = "https://app.all-hands.dev"
API_KEY_ENV_VARS = ("OPENHANDS_CLOUD_API_KEY", "OPENHANDS_API_KEY")

# Терминальные статусы start-task'а (могут эволюционировать — держим в одном месте).
START_TASK_TERMINAL = frozenset({"READY", "ERROR", "FAILED", "CANCELLED", "DONE", "COMPLETED"})
START_TASK_FAILED = frozenset({"ERROR", "FAILED", "CANCELLED"})

# Статусы исполнения разговора, означающие «работа завершена».
EXECUTION_IDLE = frozenset({"idle", "finished", "stopped", "paused"})
EXECUTION_FAILED = frozenset({"error", "failed"})

_REQUEST_TIMEOUT = 30.0
_START_TIMEOUT = 120.0


def resolve_api_key(api_key: str | None = None) -> str:
    """Взять ключ из аргумента или env; отсутствие ключа — OpenHandsAuthError."""
    if api_key:
        return api_key
    for env_name in API_KEY_ENV_VARS:
        value = os.getenv(env_name)
        if value:
            return value
    raise OpenHandsAuthError(f"нет API-ключа OpenHands: установите одну из {API_KEY_ENV_VARS}")


class OpenHandsClient:
    """Минимальный V1-клиент: старт разговора, статус, события, ожидание.

    Args:
        api_key: явный ключ (иначе из env).
        base_url: базовый URL Cloud (по умолчанию https://app.all-hands.dev).
        transport: httpx transport (для contract-тестов без сети).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        key = resolve_api_key(api_key)
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=_REQUEST_TIMEOUT,
            transport=transport,
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_v1_url(self) -> str:
        return f"{self._base_url}/api/v1"

    def close(self) -> None:
        """Закрыть HTTP-клиент."""
        self._client.close()

    def __enter__(self) -> OpenHandsClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── низкий уровень ────────────────────────────────────────────

    def _check(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code in (401, 403):
            raise OpenHandsAuthError(f"auth отклонена (HTTP {response.status_code})")
        if response.status_code >= 400:
            raise OpenHandsAPIError(
                f"OpenHands API HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()

    # ── app server ────────────────────────────────────────────────

    def users_me(self) -> dict[str, Any]:
        """Проверка auth и данных аккаунта."""
        return self._check(self._client.get(f"{self.api_v1_url}/users/me"))

    def start_conversation(
        self,
        prompt: str,
        *,
        repository: str | None = None,
        branch: str | None = None,
        title: str | None = None,
        run: bool = True,
    ) -> dict[str, Any]:
        """Создать app-conversation (создаёт sandbox — стоит денег).

        Возвращает start-task dict: ``id`` — start_task_id; ``app_conversation_id``
        может появиться сразу или позже через ``get_start_task``.
        """
        payload: dict[str, Any] = {
            "initial_message": {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
                "run": bool(run),
            }
        }
        if repository:
            payload["selected_repository"] = repository
        if branch:
            payload["selected_branch"] = branch
        if title:
            payload["title"] = title
        return self._check(
            self._client.post(f"{self.api_v1_url}/app-conversations", json=payload, timeout=_START_TIMEOUT)
        )

    def get_start_task(self, start_task_id: str) -> dict[str, Any] | None:
        """Статус start-task'а (None, если ещё не найден)."""
        items = self._check(
            self._client.get(f"{self.api_v1_url}/app-conversations/start-tasks", params={"ids": [start_task_id]})
        )
        items = items if isinstance(items, list) else items.get("items", [])
        return items[0] if items else None

    def wait_start_task(
        self,
        start_task_id: str,
        *,
        timeout_s: float = 600,
        poll_interval_s: float = 2.0,
        max_polls: int | None = None,
        sleeper: Any = time.sleep,
    ) -> dict[str, Any]:
        """Дождаться терминального статуса start-task'а (READY/...).

        Raises:
            OpenHandsTimeoutError: не дождались за ``timeout_s``/``max_polls``.
            OpenHandsStartError: терминальный статус — ошибка.
        """
        deadline = time.monotonic() + float(timeout_s)
        polls = 0
        last: dict[str, Any] | None = None
        while True:
            if max_polls is not None and polls >= max_polls:
                raise OpenHandsTimeoutError(f"start-task {start_task_id}: исчерпан max_polls={max_polls}")
            if time.monotonic() >= deadline:
                raise OpenHandsTimeoutError(f"start-task {start_task_id}: timeout {timeout_s}s")
            last = self.get_start_task(start_task_id) or last
            polls += 1
            status = str((last or {}).get("status", "")).upper()
            if status in START_TASK_FAILED:
                raise OpenHandsStartError(f"start-task {start_task_id} завершился со статусом {status}")
            if status in START_TASK_TERMINAL:
                return last or {}
            sleeper(min(poll_interval_s, max(0.0, deadline - time.monotonic())))

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Запись app-conversation (None, если не найдена)."""
        items = self._check(
            self._client.get(f"{self.api_v1_url}/app-conversations", params={"ids": [conversation_id]})
        )
        items = items if isinstance(items, list) else items.get("items", [])
        return items[0] if items else None

    def execution_status(self, conversation_id: str) -> str:
        """Текущий execution_status разговора ("" — запись не найдена)."""
        conv = self.get_conversation(conversation_id) or {}
        return str(conv.get("execution_status") or conv.get("status") or "").lower()

    def wait_execution(
        self,
        conversation_id: str,
        *,
        timeout_s: float = 1800,
        poll_interval_s: float = 10.0,
        max_polls: int | None = None,
        sleeper: Any = time.sleep,
    ) -> str:
        """Дождаться завершения исполнения (idle/finished/...).

        Returns: финальный execution_status.

        Raises:
            OpenHandsTimeoutError: не дождались за ``timeout_s``/``max_polls``.
            OpenHandsAPIError: execution завершился ошибкой.
        """
        deadline = time.monotonic() + float(timeout_s)
        polls = 0
        while True:
            if max_polls is not None and polls >= max_polls:
                raise OpenHandsTimeoutError(f"conversation {conversation_id}: исчерпан max_polls={max_polls}")
            if time.monotonic() >= deadline:
                raise OpenHandsTimeoutError(f"conversation {conversation_id}: timeout {timeout_s}s")
            status = self.execution_status(conversation_id)
            polls += 1
            if status in EXECUTION_FAILED:
                raise OpenHandsAPIError(f"conversation {conversation_id}: execution_status={status}")
            if status in EXECUTION_IDLE:
                return status
            sleeper(min(poll_interval_s, max(0.0, deadline - time.monotonic())))

    def events_search(self, conversation_id: str, *, limit: int = 100) -> dict[str, Any]:
        """События разговора (свежие последние, ограничение limit ≤ 100)."""
        limit = max(1, min(int(limit), 100))
        return self._check(
            self._client.get(
                f"{self.api_v1_url}/conversation/{conversation_id}/events/search",
                params={"limit": limit},
            )
        )

    def events_count(self, conversation_id: str) -> dict[str, Any]:
        """Число событий разговора."""
        return self._check(
            self._client.get(f"{self.api_v1_url}/conversation/{conversation_id}/events/count")
        )

    def conversation_url(self, conversation_id: str) -> str:
        """Публичный URL разговора в Cloud UI."""
        return f"{self._base_url}/conversations/{conversation_id}"
