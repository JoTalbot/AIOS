"""Contract-тесты OpenHandsClient против V1 app server API.

Без сети и без моков бизнес-логики: httpx.MockTransport эмулирует HTTP-уровень,
клиент выполняет реальный код запросов/парсинга/ожидания.
"""

import json

import httpx
import pytest

from aios_core.openhands import (
    OpenHandsAPIError,
    OpenHandsAuthError,
    OpenHandsClient,
    OpenHandsStartError,
    OpenHandsTimeoutError,
    resolve_api_key,
)

BASE = "https://app.all-hands.dev"


def make_client(handler) -> OpenHandsClient:
    return OpenHandsClient(api_key="test-key", transport=httpx.MockTransport(handler))


class TestAuth:
    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENHANDS_CLOUD_API_KEY", raising=False)
        monkeypatch.delenv("OPENHANDS_API_KEY", raising=False)
        with pytest.raises(OpenHandsAuthError):
            resolve_api_key()

    def test_env_key_preferred(self, monkeypatch):
        monkeypatch.setenv("OPENHANDS_API_KEY", "fallback")
        monkeypatch.setenv("OPENHANDS_CLOUD_API_KEY", "preferred")
        assert resolve_api_key() == "preferred"

    def test_bearer_header_sent(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"id": "u1"})

        with make_client(handler) as client:
            client.users_me()
        assert seen["auth"] == "Bearer test-key"

    def test_401_maps_to_auth_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"detail": "nope"})

        with make_client(handler) as client, pytest.raises(OpenHandsAuthError):
            client.users_me()

    def test_500_maps_to_api_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        with make_client(handler) as client:
            with pytest.raises(OpenHandsAPIError) as exc:
                client.users_me()
            assert exc.value.status_code == 500


class TestStartConversation:
    def test_payload_contract(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["payload"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "st-1", "status": "WORKING"})

        with make_client(handler) as client:
            result = client.start_conversation(
                "Сделай X", repository="JoTalbot/AIOS", branch="agent/oh-t1", title="t1"
            )
        assert result["id"] == "st-1"
        msg = seen["payload"]["initial_message"]
        assert msg["content"] == [{"type": "text", "text": "Сделай X"}]
        assert msg["run"] is True
        assert seen["payload"]["selected_repository"] == "JoTalbot/AIOS"
        assert seen["payload"]["selected_branch"] == "agent/oh-t1"

    def test_optional_fields_omitted(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["payload"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "st-2"})

        with make_client(handler) as client:
            client.start_conversation("probe")
        assert "selected_repository" not in seen["payload"]
        assert "selected_branch" not in seen["payload"]
        assert "title" not in seen["payload"]


class TestWaitStartTask:
    def test_ready_after_poll(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            status = "WORKING" if calls["n"] < 3 else "READY"
            return httpx.Response(200, json=[{"id": "st-1", "status": status, "app_conversation_id": "c-1"}])

        with make_client(handler) as client:
            task = client.wait_start_task("st-1", max_polls=10, sleeper=lambda s: None)
        assert task["status"] == "READY"
        assert task["app_conversation_id"] == "c-1"

    def test_failed_status_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": "st-1", "status": "ERROR"}])

        with make_client(handler) as client, pytest.raises(OpenHandsStartError):
            client.wait_start_task("st-1", max_polls=5, sleeper=lambda s: None)

    def test_max_polls_timeout(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": "st-1", "status": "WORKING"}])

        with make_client(handler) as client, pytest.raises(OpenHandsTimeoutError):
            client.wait_start_task("st-1", max_polls=2, sleeper=lambda s: None)


class TestWaitExecution:
    def _handler(self, statuses):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            status = statuses[min(calls["n"] - 1, len(statuses) - 1)]
            return httpx.Response(200, json=[{"id": "c-1", "execution_status": status}])

        return handler

    def test_reaches_idle(self):
        with make_client(self._handler(["running", "running", "idle"])) as client:
            assert client.wait_execution("c-1", max_polls=5, sleeper=lambda s: None) == "idle"

    def test_error_status_raises(self):
        with make_client(self._handler(["running", "error"])) as client, pytest.raises(OpenHandsAPIError):
            client.wait_execution("c-1", max_polls=5, sleeper=lambda s: None)

    def test_max_polls_timeout(self):
        with make_client(self._handler(["running"])) as client, pytest.raises(OpenHandsTimeoutError):
            client.wait_execution("c-1", max_polls=2, sleeper=lambda s: None)


class TestEvents:
    def test_events_search_limit_capped(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["limit"] = request.url.params["limit"]
            return httpx.Response(200, json={"items": []})

        with make_client(handler) as client:
            client.events_search("c-1", limit=500)
        assert seen["limit"] == "100"

    def test_conversation_url(self):
        with make_client(lambda r: httpx.Response(200, json={})) as client:
            assert client.conversation_url("c-1") == f"{BASE}/conversations/c-1"
