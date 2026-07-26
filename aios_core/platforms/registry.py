"""Platform Registry — управление всеми платформенными адаптерами."""
from __future__ import annotations
from typing import Dict, Type
from .base import PlatformAdapter
from .olx_adapter import OLXAdapter
from .instagram_adapter import InstagramAdapter

class PlatformRegistry:
    """Реестр всех доступных платформ."""
    
    def __init__(self):
        self._adapters: Dict[str, PlatformAdapter] = {}
        self._adapter_classes: Dict[str, Type[PlatformAdapter]] = {
            "olx": OLXAdapter,
            "instagram": InstagramAdapter,
        }

    def register_adapter(self, platform: str, config: Dict = None):
        """Зарегистрировать адаптер для платформы."""
        if platform not in self._adapter_classes:
            raise ValueError(f"Неизвестная платформа: {platform}")
        
        adapter_class = self._adapter_classes[platform]
        self._adapters[platform] = adapter_class(config or {})

    def get_adapter(self, platform: str) -> PlatformAdapter:
        """Получить адаптер для платформы."""
        if platform not in self._adapters:
            raise KeyError(f"Платформа {platform} не зарегистрирована")
        return self._adapters[platform]

    def list_platforms(self) -> list:
        """Список зарегистрированных платформ."""
        return list(self._adapters.keys())

    async def health_check_all(self) -> Dict[str, bool]:
        """Проверить здоровье всех платформ."""
        results = {}
        for platform, adapter in self._adapters.items():
            try:
                results[platform] = await adapter.health_check()
            except Exception:
                results[platform] = False
        return results
