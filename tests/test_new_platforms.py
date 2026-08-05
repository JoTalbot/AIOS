"""Tests for new platform adapters."""

import pytest

from aios_core.platforms.facebook_adapter import FacebookAdapter
from aios_core.platforms.prom_adapter import PromAdapter
from aios_core.platforms.registry import PlatformRegistry
from aios_core.platforms.viber_adapter import ViberAdapter
from aios_core.platforms.whatsapp_adapter import WhatsAppAdapter


def test_registry_has_all_platforms():
    """Реестр знает все 6 платформ."""
    registry = PlatformRegistry()
    available = registry.list_available_platforms()
    assert "olx" in available
    assert "instagram" in available
    assert "prom" in available
    assert "facebook" in available
    assert "viber" in available
    assert "whatsapp" in available


def test_register_all_platforms():
    """Можно зарегистрировать все платформы."""
    registry = PlatformRegistry()
    for platform in ["olx", "instagram", "prom", "facebook", "viber", "whatsapp"]:
        registry.register_adapter(platform)

    assert len(registry.list_platforms()) == 6


@pytest.mark.asyncio
async def test_prom_send(monkeypatch):
    adapter = PromAdapter()

    class _FakeResp:
        def json(self):
            return {"message_id": "prom_1"}

    async def fake_request(method, url, **kwargs):
        return _FakeResp()

    monkeypatch.setattr(adapter, "_make_request", fake_request)
    result = await adapter.send_message("user_1", "Тест")
    assert result.platform == "prom"


@pytest.mark.asyncio
async def test_facebook_send():
    adapter = FacebookAdapter()
    result = await adapter.send_message("user_1", "Тест")
    assert result.platform == "facebook"


@pytest.mark.asyncio
async def test_viber_send():
    adapter = ViberAdapter()
    result = await adapter.send_message("user_1", "Тест")
    assert result.platform == "viber"


@pytest.mark.asyncio
async def test_whatsapp_send():
    adapter = WhatsAppAdapter()
    result = await adapter.send_message("user_1", "Тест")
    assert result.platform == "whatsapp"
