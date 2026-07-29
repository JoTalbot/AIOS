"""Orchestrator — связывает AI Advisor + Telegram + Platforms."""

from __future__ import annotations

from typing import Any

from ..platforms.registry import PlatformRegistry
from .ai_advisor import AIAdvisor
from .telegram_bot import TelegramApprovalBot


class AdvisorOrchestrator:
    """Оркестратор полного цикла обработки сообщений."""

    def __init__(self, advisor: AIAdvisor, telegram_bot: TelegramApprovalBot, platform_registry: PlatformRegistry):
        self.advisor = advisor
        self.telegram_bot = telegram_bot
        self.platform_registry = platform_registry

        # Регистрируем callbacks для Telegram-бота
        self.telegram_bot.on_approved(self._on_draft_approved)
        self.telegram_bot.on_rejected(self._on_draft_rejected)

    async def handle_incoming_message(
        self, platform: str, message_id: str, text: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Полный цикл: входящее → обработка → Telegram → отправка."""

        # 1. Обработка через AI Advisor
        result = await self.advisor.process_incoming_message(
            message_id=message_id, platform=platform, incoming_text=text, context=context
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
