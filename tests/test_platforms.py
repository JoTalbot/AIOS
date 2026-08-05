"""Tests for Platform Adapters."""

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.platforms.instagram_adapter import InstagramAdapter
from aios_core.platforms.olx_adapter import OLXAdapter
from aios_core.platforms.registry import PlatformRegistry


def test_platform_registry():
    """Регистрация и получение адаптеров."""
    registry = PlatformRegistry()
    registry.register_adapter("olx", {"client_id": "test"})
    registry.register_adapter("instagram", {"access_token": "test"})

    assert "olx" in registry.list_platforms()
    assert "instagram" in registry.list_platforms()

    olx = registry.get_adapter("olx")
    assert isinstance(olx, OLXAdapter)


def test_unknown_platform():
    """Ошибка при неизвестной платформе."""
    registry = PlatformRegistry()
    with pytest.raises(ValueError):
        registry.register_adapter("unknown_platform")


def test_missing_adapter():
    """Ошибка при запросе незарегистрированного адаптера."""
    registry = PlatformRegistry()
    with pytest.raises(KeyError):
        registry.get_adapter("olx")


def _offline_olx(monkeypatch, adapter):
    """Токен предустановлен, сеть замокана — тесты без живых запросов."""
    adapter.access_token = "test-token"
    adapter._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    async def fake_request(method, url, json_data=None, **kwargs):
        return {"data": []}

    monkeypatch.setattr(adapter, "_make_request", fake_request)


@pytest.mark.asyncio
async def test_olx_adapter_receive(monkeypatch):
    """OLX adapter может получать сообщения (заглушка)."""
    adapter = OLXAdapter({"client_id": "test"})
    _offline_olx(monkeypatch, adapter)
    messages = await adapter.receive_messages()
    assert isinstance(messages, list)


@pytest.mark.asyncio
async def test_olx_adapter_send(monkeypatch):
    """OLX adapter может отправлять сообщения."""
    adapter = OLXAdapter({"client_id": "test"})
    _offline_olx(monkeypatch, adapter)
    result = await adapter.send_message("user_123", "Тестовое сообщение")
    assert result.platform == "olx"
    assert result.recipient_id == "user_123"
    assert result.text == "Тестовое сообщение"


@pytest.mark.asyncio
async def test_instagram_adapter_send(monkeypatch):
    """Instagram adapter может отправлять сообщения."""
    adapter = InstagramAdapter({"access_token": "test"})

    class _FakeResp:
        def json(self):
            return {"id": "msg_1"}

    async def fake_request(method=None, url=None, **kwargs):
        return _FakeResp()

    monkeypatch.setattr(adapter, "_make_request", fake_request)
    result = await adapter.send_message("user_456", "Привет!")
    assert result.platform == "instagram"
    assert result.recipient_id == "user_456"


@pytest.mark.asyncio
async def test_health_check_all():
    """Проверка здоровья всех платформ."""
    registry = PlatformRegistry()
    registry.register_adapter("olx")
    registry.register_adapter("instagram")

    results = await registry.health_check_all()
    assert results["olx"] is True
    assert results["instagram"] is True
