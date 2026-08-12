"""Telegram Bot for Manager Approval of Drafts — Real Integration."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class PendingDraft:
    draft_id: str
    platform: str
    message_id: str
    intent: str
    language: str
    text: str
    telegram_message_id: int | None = None


class TelegramApprovalBot:
    """Реальный Telegram-бот для одобрения черновиков."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        from tg_bot.credentials import read_systemd_credential, secret_from_env_or_credential

        self.bot_token = bot_token or secret_from_env_or_credential(
            "TELEGRAM_BOT_TOKEN", "AIOS_TELEGRAM_TOKEN", credential="telegram_token"
        )
        self.chat_id = (
            chat_id
            or os.getenv("TELEGRAM_CHAT_ID")
            or read_systemd_credential("telegram_owner_chat_id")
        )
        self.pending_drafts: dict[str, PendingDraft] = {}
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        self._on_approved: Callable | None = None
        self._on_rejected: Callable | None = None

    def on_approved(self, callback: Callable):
        """Декоратор для регистрации callback при одобрении."""
        self._on_approved = callback
        return callback

    def on_rejected(self, callback: Callable):
        """Декоратор для регистрации callback при отклонении."""
        self._on_rejected = callback
        return callback

    async def _send_telegram_message(self, text: str, reply_markup: dict | None = None) -> int | None:
        """Отправить сообщение в Telegram."""
        if not self.bot_token or not self.chat_id:
            print("⚠️  Telegram bot не настроен (нет токена/chat_id)")
            return None

        try:
            async with httpx.AsyncClient() as client:
                payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
                if reply_markup:
                    payload["reply_markup"] = reply_markup

                response = await client.post(f"{self.api_base}/sendMessage", json=payload, timeout=10.0)
                response.raise_for_status()
                return response.json()["result"]["message_id"]
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
            return None

    async def send_draft_for_approval(self, draft_data: dict[str, Any]) -> str:
        """Отправить черновик менеджеру на одобрение."""
        draft_id = draft_data["draft_id"]

        self.pending_drafts[draft_id] = PendingDraft(
            draft_id=draft_id,
            platform=draft_data["platform"],
            message_id=draft_data["message_id"],
            intent=draft_data["intent"],
            language=draft_data["language"],
            text=draft_data["draft_text"],
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
                    {"text": "❌ Отклонить", "callback_data": f"reject_{draft_id}"},
                ],
                [{"text": "✏️ Изменить", "callback_data": f"edit_{draft_id}"}],
            ]
        }

        msg_id = await self._send_telegram_message(message, reply_markup)
        if msg_id:
            self.pending_drafts[draft_id].telegram_message_id = msg_id

        return draft_id

    async def handle_callback(self, callback_data: str) -> dict[str, Any]:
        """Обработать callback от inline-кнопок."""
        if callback_data.startswith("approve_"):
            draft_id = callback_data.replace("approve_", "")
            return await self.approve_draft(draft_id)
        elif callback_data.startswith("reject_"):
            draft_id = callback_data.replace("reject_", "")
            return await self.reject_draft(draft_id)
        return {"status": "unknown"}

    async def approve_draft(self, draft_id: str) -> dict[str, Any]:
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

    async def reject_draft(self, draft_id: str, reason: str = "") -> dict[str, Any]:
        """Отклонить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}

        draft = self.pending_drafts.pop(draft_id)

        await self._send_telegram_message(
            f"❌ Черновик <code>{draft_id}</code> отклонён" + (f"\nПричина: {reason}" if reason else "")
        )

        if self._on_rejected:
            await self._on_rejected(draft, reason)

        return {"status": "rejected", "draft_id": draft_id}

    async def get_updates(self, offset: int = 0) -> list:
        """Получить новые обновления от Telegram (polling)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35.0
                )
                response.raise_for_status()
                return response.json().get("result", [])
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            return []
