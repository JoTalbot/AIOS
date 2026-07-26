#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "🚀 Применяю: Webhooks + Telegram-интеграция + 4 новые платформы..."

# === 1. Webhook endpoints (Starlette) ===
mkdir -p aios_core/webhooks

cat > aios_core/webhooks/router.py << 'PYEOF'
"""Webhook Router — endpoints для получения входящих сообщений от платформ."""
from __future__ import annotations
import os
import hmac
import hashlib
from typing import Dict, Any
from starlette.routing import Router
from starlette.requests import Request
from starlette.responses import JSONResponse
from datetime import datetime

router = Router()

# === Безопасность: проверка подписи ===
def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Проверить HMAC-SHA256 подпись webhook."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# === Instagram Webhook (Meta) ===
@router.get("/webhooks/instagram")
async def instagram_verify(request: Request):
    """Instagram verification challenge (GET)."""
    params = request.query_params
    if params.get("hub.verify_token") == os.getenv("INSTAGRAM_VERIFY_TOKEN"):
        return JSONResponse({"challenge": params.get("hub.challenge")})
    return JSONResponse({"error": "Invalid token"}, status_code=403)

@router.post("/webhooks/instagram")
async def instagram_webhook(request: Request):
    """Instagram incoming messages (POST)."""
    body = await request.body()
    # TODO: Проверка подписи X-Hub-Signature-256
    data = await request.json()
    
    # Парсинг Instagram webhook payload
    messages = []
    for entry in data.get("entry", []):
        for messaging in entry.get("messaging", []):
            if "message" in messaging:
                messages.append({
                    "platform": "instagram",
                    "sender_id": messaging["sender"]["id"],
                    "text": messaging["message"].get("text", ""),
                    "message_id": messaging["message"]["mid"],
                    "timestamp": datetime.fromtimestamp(messaging["timestamp"])
                })
    
    # TODO: Передать в AIAdvisor pipeline
    # for msg in messages:
    #     await advisor.process_and_respond(...)
    
    return JSONResponse({"status": "ok", "processed": len(messages)})

# === OLX Webhook ===
@router.post("/webhooks/olx")
async def olx_webhook(request: Request):
    """OLX incoming messages."""
    body = await request.body()
    signature = request.headers.get("X-OLX-Signature", "")
    secret = os.getenv("OLX_WEBHOOK_SECRET", "")
    
    if secret and not verify_signature(body, signature, secret):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)
    
    data = await request.json()
    # TODO: Парсинг OLX payload и передача в AIAdvisor
    
    return JSONResponse({"status": "ok"})

# === Viber Webhook ===
@router.post("/webhooks/viber")
async def viber_webhook(request: Request):
    """Viber incoming messages."""
    data = await request.json()
    if data.get("event") == "message":
        message = {
            "platform": "viber",
            "sender_id": data["sender"]["id"],
            "sender_name": data["sender"]["name"],
            "text": data["message"].get("text", ""),
            "message_id": data["message_token"]
        }
        # TODO: Передать в AIAdvisor
    return JSONResponse({"status": "ok"})

# === WhatsApp (Meta Cloud API) ===
@router.get("/webhooks/whatsapp")
async def whatsapp_verify(request: Request):
    """WhatsApp verification challenge."""
    params = request.query_params
    if params.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return JSONResponse(content=params.get("hub.challenge"))
    return JSONResponse({"error": "Invalid token"}, status_code=403)

@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp incoming messages."""
    data = await request.json()
    messages = []
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") == "text":
                    messages.append({
                        "platform": "whatsapp",
                        "sender_id": msg["from"],
                        "text": msg["text"]["body"],
                        "message_id": msg["id"]
                    })
    return JSONResponse({"status": "ok", "processed": len(messages)})

# === Facebook Messenger ===
@router.get("/webhooks/facebook")
async def facebook_verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == os.getenv("FACEBOOK_VERIFY_TOKEN"):
        return JSONResponse(content=params.get("hub.challenge"))
    return JSONResponse({"error": "Invalid token"}, status_code=403)

@router.post("/webhooks/facebook")
async def facebook_webhook(request: Request):
    """Facebook Messenger incoming messages."""
    data = await request.json()
    messages = []
    for entry in data.get("entry", []):
        for messaging in entry.get("messaging", []):
            if "message" in messaging:
                messages.append({
                    "platform": "facebook",
                    "sender_id": messaging["sender"]["id"],
                    "text": messaging["message"].get("text", ""),
                    "message_id": messaging["message"]["mid"]
                })
    return JSONResponse({"status": "ok", "processed": len(messages)})
PYEOF

# === 2. Обновляем Telegram-бот — реальная интеграция ===
cat > aios_core/advisor/telegram_bot.py << 'PYEOF'
"""Telegram Bot for Manager Approval of Drafts — Real Integration."""
from __future__ import annotations
import os
import httpx
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class PendingDraft:
    draft_id: str
    platform: str
    message_id: str
    intent: str
    language: str
    text: str
    telegram_message_id: Optional[int] = None

class TelegramApprovalBot:
    """Реальный Telegram-бот для одобрения черновиков."""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.pending_drafts: Dict[str, PendingDraft] = {}
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        self._on_approved: Optional[Callable] = None
        self._on_rejected: Optional[Callable] = None

    def on_approved(self, callback: Callable):
        """Декоратор для регистрации callback при одобрении."""
        self._on_approved = callback
        return callback

    def on_rejected(self, callback: Callable):
        """Декоратор для регистрации callback при отклонении."""
        self._on_rejected = callback
        return callback

    async def _send_telegram_message(self, text: str, reply_markup: Dict = None) -> Optional[int]:
        """Отправить сообщение в Telegram."""
        if not self.bot_token or not self.chat_id:
            print("⚠️  Telegram bot не настроен (нет токена/chat_id)")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                
                response = await client.post(
                    f"{self.api_base}/sendMessage",
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()["result"]["message_id"]
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
            return None

    async def send_draft_for_approval(self, draft_data: Dict[str, Any]) -> str:
        """Отправить черновик менеджеру на одобрение."""
        draft_id = draft_data["draft_id"]
        
        self.pending_drafts[draft_id] = PendingDraft(
            draft_id=draft_id,
            platform=draft_data["platform"],
            message_id=draft_data["message_id"],
            intent=draft_data["intent"],
            language=draft_data["language"],
            text=draft_data["draft_text"]
        )
        
        message = (
            f"🤖 <b>Новый черновик ответа</b>\n\n"
            f"📱 <b>Платформа:</b> {draft_data['platform']}\n"
            f"🎯 <b>Намерение:</b> {draft_data['intent']}\n"
            f"🌍 <b>Язык:</b> {draft_data['language']}\n\n"
            f"📝 <b>Текст:</b>\n<pre>{draft_data['draft_text']}</pre>"
        )
        
        # Inline-кнопки для одобрения/отклонения
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Одобрить", "callback_data": f"approve_{draft_id}"},
                    {"text": "❌ Отклонить", "callback_data": f"reject_{draft_id}"}
                ],
                [
                    {"text": "✏️ Изменить", "callback_data": f"edit_{draft_id}"}
                ]
            ]
        }
        
        msg_id = await self._send_telegram_message(message, reply_markup)
        if msg_id:
            self.pending_drafts[draft_id].telegram_message_id = msg_id
        
        return draft_id

    async def handle_callback(self, callback_data: str) -> Dict[str, Any]:
        """Обработать callback от inline-кнопок."""
        if callback_data.startswith("approve_"):
            draft_id = callback_data.replace("approve_", "")
            return await self.approve_draft(draft_id)
        elif callback_data.startswith("reject_"):
            draft_id = callback_data.replace("reject_", "")
            return await self.reject_draft(draft_id)
        return {"status": "unknown"}

    async def approve_draft(self, draft_id: str) -> Dict[str, Any]:
        """Одобрить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}
        
        draft = self.pending_drafts.pop(draft_id)
        
        # Уведомление в Telegram
        await self._send_telegram_message(
            f"✅ Черновик <code>{draft_id}</code> одобрен и отправлен на {draft.platform}"
        )
        
        # Вызов callback для реальной отправки через платформу
        if self._on_approved:
            await self._on_approved(draft)
        
        return {"status": "approved", "draft_id": draft_id, "draft": draft}

    async def reject_draft(self, draft_id: str, reason: str = "") -> Dict[str, Any]:
        """Отклонить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}
        
        draft = self.pending_drafts.pop(draft_id)
        
        await self._send_telegram_message(
            f"❌ Черновик <code>{draft_id}</code> отклонён"
            + (f"\nПричина: {reason}" if reason else "")
        )
        
        if self._on_rejected:
            await self._on_rejected(draft, reason)
        
        return {"status": "rejected", "draft_id": draft_id}

    async def get_updates(self, offset: int = 0) -> list:
        """Получить новые обновления от Telegram (polling)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=35.0
                )
                response.raise_for_status()
                return response.json().get("result", [])
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            return []
PYEOF

# === 3. Новые платформы: Prom.ua, Facebook, Viber, WhatsApp ===

cat > aios_core/platforms/prom_adapter.py << 'PYEOF'
"""Prom.ua Platform Adapter."""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class PromAdapter(PlatformAdapter):
    """Адаптер для Prom.ua."""
    
    API_URL = "https://my.prom.ua/api/v1"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.api_key = self.config.get("api_key") or os.getenv("PROM_API_KEY")
        self.client_id = self.config.get("client_id") or os.getenv("PROM_CLIENT_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # TODO: GET /chat_messages
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /chat_messages
        return SentMessage(
            message_id=f"prom_{int(datetime.utcnow().timestamp())}",
            platform="prom", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": "prom"}
PYEOF

cat > aios_core/platforms/facebook_adapter.py << 'PYEOF'
"""Facebook Messenger Platform Adapter (Meta Graph API)."""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class FacebookAdapter(PlatformAdapter):
    """Адаптер для Facebook Messenger."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.page_id = self.config.get("page_id") or os.getenv("FACEBOOK_PAGE_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # Facebook использует Webhooks (см. aios_core/webhooks/router.py)
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /{page_id}/messages (Send API)
        return SentMessage(
            message_id=f"fb_{int(datetime.utcnow().timestamp())}",
            platform="facebook", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": "facebook"}
PYEOF

cat > aios_core/platforms/viber_adapter.py << 'PYEOF'
"""Viber Platform Adapter."""
from __future__ import annotations
import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class ViberAdapter(PlatformAdapter):
    """Адаптер для Viber Public Accounts."""
    
    API_URL = "https://chatapi.viber.com/pa"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.auth_token = self.config.get("auth_token") or os.getenv("VIBER_AUTH_TOKEN")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # Viber использует Webhooks
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /send_message
        return SentMessage(
            message_id=f"viber_{int(datetime.utcnow().timestamp())}",
            platform="viber", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        # TODO: POST /get_user_details
        return {"user_id": user_id, "platform": "viber"}

    async def set_webhook(self, url: str) -> bool:
        """Настроить webhook для Viber."""
        # TODO: POST /set_webhook
        return True
PYEOF

cat > aios_core/platforms/whatsapp_adapter.py << 'PYEOF'
"""WhatsApp Platform Adapter (Meta Cloud API)."""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import PlatformAdapter, IncomingMessage, SentMessage

class WhatsAppAdapter(PlatformAdapter):
    """Адаптер для WhatsApp Business (Meta Cloud API)."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.access_token = self.config.get("access_token") or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = self.config.get("phone_number_id") or os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        # WhatsApp использует Webhooks
        return []

    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        # TODO: POST /{phone_number_id}/messages
        return SentMessage(
            message_id=f"wa_{int(datetime.utcnow().timestamp())}",
            platform="whatsapp", recipient_id=recipient_id,
            text=text, timestamp=datetime.utcnow()
        )

    async def mark_as_read(self, message_id: str) -> bool:
        # TODO: POST /{phone_number_id}/messages с status=mark_as_read
        return True

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": "whatsapp"}
PYEOF

# === 4. Обновляем Platform Registry ===
cat > aios_core/platforms/registry.py << 'PYEOF'
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
PYEOF

# === 5. Интеграция Telegram-бота в AI Advisor ===
cat > aios_core/advisor/orchestrator.py << 'PYEOF'
"""Orchestrator — связывает AI Advisor + Telegram + Platforms."""
from __future__ import annotations
from typing import Dict, Any
from .ai_advisor import AIAdvisor
from .telegram_bot import TelegramApprovalBot
from ..platforms.registry import PlatformRegistry

class AdvisorOrchestrator:
    """Оркестратор полного цикла обработки сообщений."""
    
    def __init__(self, advisor: AIAdvisor, telegram_bot: TelegramApprovalBot,
                 platform_registry: PlatformRegistry):
        self.advisor = advisor
        self.telegram_bot = telegram_bot
        self.platform_registry = platform_registry
        
        # Регистрируем callbacks для Telegram-бота
        self.telegram_bot.on_approved(self._on_draft_approved)
        self.telegram_bot.on_rejected(self._on_draft_rejected)

    async def handle_incoming_message(self, platform: str, message_id: str,
                                      text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Полный цикл: входящее → обработка → Telegram → отправка."""
        
        # 1. Обработка через AI Advisor
        result = await self.advisor.process_incoming_message(
            message_id=message_id, platform=platform,
            incoming_text=text, context=context
        )
        
        # 2. Если черновик готов — отправляем в Telegram на одобрение
        if result["status"] == "draft_ready":
            await self.telegram_bot.send_draft_for_approval(result)
        
        # 3. Если эскалация — уведомляем менеджера
        if result["status"] == "escalated":
            await self.telegram_bot._send_telegram_message(
                f"🚨 <b>Требует внимания!</b>\n\n"
                f"Платформа: {platform}\n"
                f"Причина: {result.get('escalation_reason', 'негатив')}\n"
                f"Текст: {text}"
            )
        
        return result

    async def _on_draft_approved(self, draft):
        """Callback: черновик одобрен — отправляем через платформу."""
        try:
            adapter = self.platform_registry.get_adapter(draft.platform)
            await adapter.send_message(draft.message_id, draft.text)
            self.advisor.metrics.record_draft_approved()
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")

    async def _on_draft_rejected(self, draft, reason: str):
        """Callback: черновик отклонён."""
        self.advisor.metrics.record_draft_rejected()
PYEOF

# === 6. Тесты для новых платформ ===
cat > tests/test_new_platforms.py << 'PYEOF'
"""Tests for new platform adapters."""
import pytest
from aios_core.platforms.registry import PlatformRegistry
from aios_core.platforms.prom_adapter import PromAdapter
from aios_core.platforms.facebook_adapter import FacebookAdapter
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
async def test_prom_send():
    adapter = PromAdapter()
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
PYEOF

# === 7. Тесты для Telegram-бота ===
cat > tests/test_telegram_bot.py << 'PYEOF'
"""Tests for Telegram Approval Bot."""
import pytest
from aios_core.advisor.telegram_bot import TelegramApprovalBot

@pytest.mark.asyncio
async def test_send_draft_for_approval():
    """Бот принимает черновик на одобрение."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    draft_id = await bot.send_draft_for_approval({
        "draft_id": "draft_001",
        "platform": "olx",
        "message_id": "msg_001",
        "intent": "price_inquiry",
        "language": "uk",
        "draft_text": "Тестовый черновик"
    })
    assert draft_id == "draft_001"
    assert draft_id in bot.pending_drafts

@pytest.mark.asyncio
async def test_approve_draft():
    """Одобрение черновика."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    await bot.send_draft_for_approval({
        "draft_id": "draft_002", "platform": "olx",
        "message_id": "msg_002", "intent": "greeting",
        "language": "ru", "draft_text": "Привет!"
    })
    
    result = await bot.approve_draft("draft_002")
    assert result["status"] == "approved"
    assert "draft_002" not in bot.pending_drafts

@pytest.mark.asyncio
async def test_reject_draft():
    """Отклонение черновика."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    await bot.send_draft_for_approval({
        "draft_id": "draft_003", "platform": "olx",
        "message_id": "msg_003", "intent": "greeting",
        "language": "ru", "draft_text": "Тест"
    })
    
    result = await bot.reject_draft("draft_003", reason="Неверный текст")
    assert result["status"] == "rejected"

@pytest.mark.asyncio
async def test_handle_callback_approve():
    """Обработка callback approve_."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    await bot.send_draft_for_approval({
        "draft_id": "draft_004", "platform": "olx",
        "message_id": "msg_004", "intent": "greeting",
        "language": "ru", "draft_text": "Тест"
    })
    
    result = await bot.handle_callback("approve_draft_004")
    assert result["status"] == "approved"

@pytest.mark.asyncio
async def test_unknown_draft():
    """Ошибка при неизвестном черновике."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    result = await bot.approve_draft("unknown_id")
    assert result["status"] == "error"
PYEOF

# === 8. Обновляем .env.example ===
cat > .env.example << 'ENVEOF'
# === LLM Configuration ===
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# === Telegram Bot (для одобрения черновиков) ===
TELEGRAM_BOT_TOKEN=your-bot-token-from-BotFather
TELEGRAM_CHAT_ID=your-chat-id

# === OLX ===
OLX_CLIENT_ID=
OLX_CLIENT_SECRET=
OLX_ACCESS_TOKEN=
OLX_WEBHOOK_SECRET=

# === Instagram (Meta) ===
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
INSTAGRAM_VERIFY_TOKEN=

# === Prom.ua ===
PROM_API_KEY=
PROM_CLIENT_ID=

# === Facebook Messenger ===
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
FACEBOOK_VERIFY_TOKEN=

# === Viber ===
VIBER_AUTH_TOKEN=

# === WhatsApp (Meta Cloud API) ===
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
ENVEOF

# === 9. Обновляем requirements.txt ===
for pkg in "httpx>=0.27.0" "starlette>=0.36.0" "python-telegram-bot>=20.0" "pytest-asyncio>=0.21.0"; do
    grep -q "^${pkg%%[>=]*}" requirements.txt 2>/dev/null || echo "$pkg" >> requirements.txt
done

echo ""
echo "✅ Все модули успешно применены!"
echo ""
echo "📦 Созданные файлы:"
echo "   • aios_core/webhooks/router.py (5 webhook endpoints)"
echo "   • aios_core/advisor/telegram_bot.py (реальная интеграция)"
echo "   • aios_core/advisor/orchestrator.py (связка всех компонентов)"
echo "   • aios_core/platforms/prom_adapter.py"
echo "   • aios_core/platforms/facebook_adapter.py"
echo "   • aios_core/platforms/viber_adapter.py"
echo "   • aios_core/platforms/whatsapp_adapter.py"
echo "   • tests/test_new_platforms.py"
echo "   • tests/test_telegram_bot.py"
echo "   • .env.example (обновлён)"
