"""Platform Registry — управление всеми платформенными адаптерами."""

from __future__ import annotations

from .base import PlatformAdapter
from .ebay_adapter import EbayAdapter
from .facebook_adapter import FacebookAdapter
from .facebook_chrome_twin_adapter import FacebookChromeTwinAdapter
from .instagram_adapter import InstagramAdapter
from .instagram_emulator_adapter import InstagramEmulatorAdapter
from .chrome_twin_adapter import ChromeTwinAdapter
from .olx_chrome_twin_adapter import OLXChromeTwinAdapter
from .instagram_chrome_twin_adapter import InstagramChromeTwinAdapter
from .linkedin_adapter import LinkedinAdapter
from .olx_adapter import OLXAdapter
from .prom_adapter import PromAdapter
from .tiktok_adapter import TiktokAdapter
from .tiktok_chrome_twin_adapter import TiktokChromeTwinAdapter
from .tiktok_shop_adapter import TiktokShopAdapter
from .viber_adapter import ViberAdapter
from .whatsapp_adapter import WhatsAppAdapter


class PlatformRegistry:
    """Реестр всех доступных платформ."""

    def __init__(self):
        self._adapters: dict[str, PlatformAdapter] = {}
        self._adapter_classes: dict[str, type[PlatformAdapter]] = {
            "olx": OLXAdapter,
            "instagram": InstagramAdapter,
            "instagram_emulator": InstagramEmulatorAdapter,
            "chrome_twin": ChromeTwinAdapter,
            "olx_chrome_twin": OLXChromeTwinAdapter,
            "instagram_chrome_twin": InstagramChromeTwinAdapter,
            "prom": PromAdapter,
            "facebook": FacebookAdapter,
            "facebook_chrome_twin": FacebookChromeTwinAdapter,
            "viber": ViberAdapter,
            "whatsapp": WhatsAppAdapter,
            "tiktok": TiktokAdapter,
            "tiktok_chrome_twin": TiktokChromeTwinAdapter,
            "linkedin": LinkedinAdapter,
            "ebay": EbayAdapter,
            "tiktok_shop": TiktokShopAdapter,
        }

    def register_adapter(self, platform: str, config: dict | None = None):
        if platform not in self._adapter_classes:
            raise ValueError(f"Неизвестная платформа: {platform}. Доступные: {list(self._adapter_classes.keys())}")
        adapter_class = self._adapter_classes[platform]
        self._adapters[platform] = adapter_class(config or {})

    def get_adapter(self, platform: str) -> PlatformAdapter:
        if platform not in self._adapters:
            raise KeyError(f"Платформа {platform} не зарегистрирована")
        return self._adapters[platform]

    def list_platforms(self) -> list[str]:
        return list(self._adapters.keys())

    def list_available_platforms(self) -> list[str]:
        """Все платформы, которые можно зарегистрировать."""
        return list(self._adapter_classes.keys())

    async def health_check_all(self) -> dict[str, bool]:
        results = {}
        for platform, adapter in self._adapters.items():
            try:
                results[platform] = await adapter.health_check()
            except Exception:
                results[platform] = False
        return results
