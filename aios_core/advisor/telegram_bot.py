"""Telegram Bot for Manager Approval of Drafts."""
from __future__ import annotations
import os
import json
from typing import Dict, Any
from pathlib import Path

class TelegramApprovalBot:
    """Бот для одобрения черновиков через Telegram."""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.pending_drafts: Dict[str, Dict[str, Any]] = {}

    async def send_draft_for_approval(self, draft_data: Dict[str, Any]) -> str:
        """Отправить черновик менеджеру на одобрение."""
        draft_id = draft_data["draft_id"]
        self.pending_drafts[draft_id] = draft_data
        
        message = (
            f"🤖 Новый черновик ответа\n\n"
            f"📱 Платформа: {draft_data['platform']}\n"
            f"🎯 Намерение: {draft_data['intent']}\n"
            f"🌍 Язык: {draft_data['language']}\n\n"
            f"📝 Текст:\n{draft_data['draft_text']}\n\n"
            f"✅ Одобрить: /approve_{draft_id}\n"
            f"❌ Отклонить: /reject_{draft_id}"
        )
        
        # TODO: Реальный вызов Telegram API
        # await self._send_telegram_message(message)
        
        return draft_id

    async def approve_draft(self, draft_id: str) -> Dict[str, Any]:
        """Одобрить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}
        
        draft = self.pending_drafts.pop(draft_id)
        draft["status"] = "approved"
        
        # TODO: Отправить одобренный текст через Platform Adapter
        # await platform_adapter.send_message(draft["platform"], draft["message_id"], draft["draft_text"])
        
        return {"status": "approved", "draft_id": draft_id}

    async def reject_draft(self, draft_id: str, reason: str = "") -> Dict[str, Any]:
        """Отклонить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}
        
        draft = self.pending_drafts.pop(draft_id)
        draft["status"] = "rejected"
        draft["rejection_reason"] = reason
        
        return {"status": "rejected", "draft_id": draft_id}
