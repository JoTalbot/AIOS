#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "🚀 Применяю: UI для метрик + Platform Adapters (OLX, Instagram)..."

# === 1. Создаём базовый класс Platform Adapter ===
mkdir -p aios_core/platforms

cat > aios_core/platforms/base.py << 'PYEOF'
"""Base Platform Adapter — абстрактный интерфейс для всех платформ."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class IncomingMessage:
    """Входящее сообщение с платформы."""
    message_id: str
    platform: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class SentMessage:
    """Отправленное сообщение."""
    message_id: str
    platform: str
    recipient_id: str
    text: str
    timestamp: datetime
    status: str = "sent"  # sent, delivered, failed

class PlatformAdapter(ABC):
    """Абстрактный базовый класс для всех платформ."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform_name = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        """Получить новые входящие сообщения."""
        pass

    @abstractmethod
    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        """Отправить сообщение."""
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Пометить сообщение как прочитанное."""
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Получить информацию о пользователе."""
        pass

    async def health_check(self) -> bool:
        """Проверить работоспособность соединения."""
        return True
PYEOF

# === 2. OLX Adapter ===
cat > aios_core/platforms/olx_adapter.py << 'PYEOF'
"""OLX Platform Adapter — интеграция с OLX API."""
from __future__ import annotations
import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class OLXAdapter(PlatformAdapter):
    """Адаптер для OLX.ua (использует OLX API v2)."""
    
    BASE_URL = "https://www.olx.ua/api/v1"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.client_id = self.config.get("client_id") or os.getenv("OLX_CLIENT_ID")
        self.client_secret = self.config.get("client_secret") or os.getenv("OLX_CLIENT_SECRET")
        self.access_token = self.config.get("access_token") or os.getenv("OLX_ACCESS_TOKEN")
        self._token_expires = None

    async def _ensure_token(self):
        """Обновить OAuth2 токен если нужно."""
        if self.access_token and self._token_expires and datetime.utcnow() < self._token_expires:
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
        #     self._token_expires = datetime.utcnow() + timedelta(seconds=data["expires_in"])

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        """Получить новые сообщения из OLX threads."""
        await self._ensure_token()
        
        # TODO: Реальный вызов OLX API
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{self.BASE_URL}/threads",
        #         headers={"Authorization": f"Bearer {self.access_token}"},
        #         params={"last_id": since.timestamp() if since else None}
        #     )
        #     threads = response.json()["data"]
        
        # Заглушка для демонстрации
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        """Отправить ответ в OLX thread."""
        await self._ensure_token()
        
        # TODO: Реальный вызов
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.BASE_URL}/threads/{recipient_id}/messages",
        #         headers={"Authorization": f"Bearer {self.access_token}"},
        #         json={"text": text}
        #     )
        
        return SentMessage(
            message_id=f"olx_{int(datetime.utcnow().timestamp())}",
            platform="olx",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        await self._ensure_token()
        # TODO: PUT /threads/{thread_id}/read
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        await self._ensure_token()
        # TODO: GET /users/{user_id}
        return {"user_id": user_id, "platform": "olx"}
PYEOF

# === 3. Instagram Adapter ===
cat > aios_core/platforms/instagram_adapter.py << 'PYEOF'
"""Instagram Platform Adapter — интеграция с Meta Graph API."""
from __future__ import annotations
import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class InstagramAdapter(PlatformAdapter):
    """Адаптер для Instagram (Meta Graph API для Business Accounts)."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_account_id = self.config.get("account_id") or os.getenv("INSTAGRAM_ACCOUNT_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        """Получить новые сообщения из Instagram Direct."""
        # Instagram использует Webhooks для получения сообщений в реальном времени
        # Этот метод используется для initial sync или polling
        
        # TODO: Реальный вызов Graph API
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{self.GRAPH_API_URL}/{self.instagram_account_id}/conversations",
        #         params={
        #             "access_token": self.access_token,
        #             "fields": "messages{id,message,from,created_time}",
        #             "limit": 50
        #         }
        #     )
        #     conversations = response.json()["data"]
        
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        """Отправить ответ в Instagram Direct."""
        # TODO: Реальный вызов
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.GRAPH_API_URL}/{self.instagram_account_id}/messages",
        #         params={"access_token": self.access_token},
        #         json={
        #             "recipient": {"id": recipient_id},
        #             "message": {"text": text}
        #         }
        #     )
        
        return SentMessage(
            message_id=f"ig_{int(datetime.utcnow().timestamp())}",
            platform="instagram",
            recipient_id=recipient_id,
            text=text,
            timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # Instagram автоматически помечает как прочитанное при получении
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        # TODO: GET /{user_id}?fields=username,name,profile_pic
        return {"user_id": user_id, "platform": "instagram"}

    async def setup_webhook(self, webhook_url: str, verify_token: str) -> bool:
        """Настроить webhook для получения сообщений в реальном времени."""
        # TODO: POST /{app_id}/subscriptions
        # {
        #     "object": "instagram",
        #     "fields": ["messages"],
        #     "callback_url": webhook_url,
        #     "verify_token": verify_token
        # }
        return True
PYEOF

# === 4. Platform Registry ===
cat > aios_core/platforms/registry.py << 'PYEOF'
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
PYEOF

# === 5. UI для метрик с графиками ===
cat > aios_core/dashboard/views/metrics_view.py << 'PYEOF'
"""NiceGUI View for AI Advisor Metrics Dashboard."""
from __future__ import annotations
from nicegui import ui
from pathlib import Path
import json
from datetime import datetime, timedelta

def render_metrics_view(metrics_collector):
    """Отрисовка дашборда метрик AI Advisor."""
    
    ui.label('📊 AI Advisor — Метрики и аналитика').classes('text-h4 q-mb-md')
    
    # Получаем сводку
    summary = metrics_collector.get_summary()
    
    # === Карточки с основными метриками ===
    with ui.row().classes('w-full gap-4 q-mb-lg'):
        with ui.card().classes('flex-1'):
            ui.label('📝 Черновики созданы').classes('text-caption')
            ui.label(str(summary['drafts_created'])).classes('text-h3 text-primary')
        
        with ui.card().classes('flex-1'):
            ui.label('✅ Approval Rate').classes('text-caption')
            ui.label(summary['approval_rate']).classes('text-h3 text-positive')
        
        with ui.card().classes('flex-1'):
            ui.label('🚨 Эскалации').classes('text-caption')
            ui.label(str(summary['escalations'])).classes('text-h3 text-negative')
        
        with ui.card().classes('flex-1'):
            ui.label('🛡️ Нарушения').classes('text-caption')
            ui.label(str(summary['compliance_violations'])).classes('text-h3 text-warning')
    
    # === График: Топ намерений ===
    with ui.card().classes('w-full q-mb-lg'):
        ui.label('🎯 Топ намерений (Intents)').classes('text-h6')
        
        if summary['top_intents']:
            intents_data = [
                {'name': intent, 'count': count}
                for intent, count in summary['top_intents']
            ]
            
            ui.chart(
                series=[{'name': 'Количество', 'data': [d['count'] for d in intents_data]}],
                options={
                    'chart': {'type': 'bar'},
                    'xaxis': {'categories': [d['name'] for d in intents_data]},
                    'colors': ['#1976D2'],
                    'plotOptions': {'bar': {'horizontal': False}}
                }
            ).classes('w-full h-64')
        else:
            ui.label('Нет данных').classes('text-grey')
    
    # === График: Распределение тональности ===
    with ui.card().classes('w-full q-mb-lg'):
        ui.label('😠 Распределение тональности').classes('text-h6')
        
        sentiment_data = summary['sentiment_distribution']
        if any(sentiment_data.values()):
            ui.chart(
                series=[{
                    'name': 'Сообщения',
                    'data': [
                        sentiment_data.get('positive', 0),
                        sentiment_data.get('neutral', 0),
                        sentiment_data.get('negative', 0)
                    ]
                }],
                options={
                    'chart': {'type': 'pie'},
                    'labels': ['Позитивные', 'Нейтральные', 'Негативные'],
                    'colors': ['#4CAF50', '#9E9E9E', '#F44336']
                }
            ).classes('w-full h-64')
        else:
            ui.label('Нет данных').classes('text-grey')
    
    # === История за последние 7 дней ===
    with ui.card().classes('w-full'):
        ui.label('📅 История за 7 дней').classes('text-h6')
        
        history_data = []
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            metrics_file = Path(metrics_collector.storage_path) / f"{date}.json"
            if metrics_file.exists():
                data = json.loads(metrics_file.read_text())
                history_data.append({
                    'date': date,
                    'drafts': data.get('drafts_created', 0),
                    'escalations': data.get('escalations', 0)
                })
        
        if history_data:
            history_data.reverse()  # Хронологический порядок
            
            ui.chart(
                series=[
                    {'name': 'Черновики', 'data': [d['drafts'] for d in history_data]},
                    {'name': 'Эскалации', 'data': [d['escalations'] for d in history_data]}
                ],
                options={
                    'chart': {'type': 'line'},
                    'xaxis': {'categories': [d['date'] for d in history_data]},
                    'colors': ['#1976D2', '#F44336'],
                    'stroke': {'curve': 'smooth'}
                }
            ).classes('w-full h-64')
        else:
            ui.label('Нет данных за последние 7 дней').classes('text-grey')
    
    # === Кнопка обновления ===
    ui.button('🔄 Обновить', on_click=lambda: ui.navigate().reload()).classes('q-mt-md')
PYEOF

# === 6. Тесты для платформ ===
cat > tests/test_platforms.py << 'PYEOF'
"""Tests for Platform Adapters."""
import pytest
from datetime import datetime
from aios_core.platforms.registry import PlatformRegistry
from aios_core.platforms.olx_adapter import OLXAdapter
from aios_core.platforms.instagram_adapter import InstagramAdapter

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

@pytest.mark.asyncio
async def test_olx_adapter_receive():
    """OLX adapter может получать сообщения (заглушка)."""
    adapter = OLXAdapter({"client_id": "test"})
    messages = await adapter.receive_messages()
    assert isinstance(messages, list)

@pytest.mark.asyncio
async def test_olx_adapter_send():
    """OLX adapter может отправлять сообщения."""
    adapter = OLXAdapter({"client_id": "test"})
    result = await adapter.send_message("user_123", "Тестовое сообщение")
    assert result.platform == "olx"
    assert result.recipient_id == "user_123"
    assert result.text == "Тестовое сообщение"

@pytest.mark.asyncio
async def test_instagram_adapter_send():
    """Instagram adapter может отправлять сообщения."""
    adapter = InstagramAdapter({"access_token": "test"})
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
PYEOF

# === 7. Обновляем requirements.txt ===
if ! grep -q "httpx" requirements.txt 2>/dev/null; then
    echo "httpx>=0.27.0" >> requirements.txt
fi

# === 8. Интеграция Platform Registry в AI Advisor ===
cat >> aios_core/advisor/ai_advisor.py << 'PYEOF'

# === Интеграция с Platform Registry ===
from aios_core.platforms.registry import PlatformRegistry

class AIAdvisorWithPlatforms(AIAdvisor):
    """AI Advisor с интеграцией платформенных адаптеров."""
    
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        super().__init__(templates_dir, use_llm)
        self.platform_registry = PlatformRegistry()

    def register_platform(self, platform: str, config: Dict[str, Any] = None):
        """Зарегистрировать платформу."""
        self.platform_registry.register_adapter(platform, config)

    async def process_and_respond(self, platform: str, message_id: str,
                                  incoming_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Полный цикл: обработка + автоматическая отправка после одобрения."""
        
        # Обработка через основной пайплайн
        result = await self.process_incoming_message(message_id, platform, incoming_text, context)
        
        if result["status"] == "draft_ready":
            # Здесь можно интегрировать с Telegram ботом для одобрения
            # После одобрения — автоматическая отправка через платформу
            pass
        
        return result
PYEOF

echo "✅ Все модули применены!"
