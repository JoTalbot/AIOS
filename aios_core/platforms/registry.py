"""Platform Registry — управление всеми платформенными адаптерами."""
from __future__ import annotations
from typing import Dict, Type, List
from .base import PlatformAdapter
from .olx_adapter import OLXAdapter
from .instagram_adapter import InstagramAdapter
from .prom_adapter import PromAdapter
from .facebook_adapter import FacebookAdapter
from .viber_adapter import ViberAdapter
from .whatsapp_adapter import WhatsAppAdapter
from .tiktok_adapter import TiktokAdapter
from .linkedin_adapter import LinkedinAdapter
from .ebay_adapter import EbayAdapter
from .tiktok_shop_adapter import TiktokShopAdapter

class PlatformRegistry:
    """Реестр всех доступных платформ."""
    
    def __init__(self):
        self._adapters: Dict[str, PlatformAdapter] = {}
        self._adapter_classes: Dict[str, Type[PlatformAdapter]] = {
            "olx": OLXAdapter,
            "instagram": InstagramAdapter,
            "prom": PromAdapter,
            "facebook": FacebookAdapter,
            "viber": ViberAdapter,
            "whatsapp": WhatsAppAdapter,
            "tiktok": TiktokAdapter,
            "linkedin": LinkedinAdapter,
            "ebay": EbayAdapter,
            "tiktok_shop": TiktokShopAdapter,
        }

    def register_adapter(self, platform: str, config: Dict = None):
        if platform not in self._adapter_classes:
            raise ValueError(f"Неизвестная платформа: {platform}. Доступные: {list(self._adapter_classes.keys())}")
        adapter_class = self._adapter_classes[platform]
        self._adapters[platform] = adapter_class(config or {})

    def get_adapter(self, platform: str) -> PlatformAdapter:
        if platform not in self._adapters:
            raise KeyError(f"Платформа {platform} не зарегистрирована")
        return self._adapters[platform]

    def list_platforms(self) -> List[str]:
        return list(self._adapters.keys())

    def list_available_platforms(self) -> List[str]:
        """Все платформы, которые можно зарегистрировать."""
        return list(self._adapter_classes.keys())

    async def health_check_all(self) -> Dict[str, bool]:
        results = {}
        for platform, adapter in self._adapters.items():
            try:
                results[platform] = await adapter.health_check()
            except Exception:
                results[platform] = False
        return results
