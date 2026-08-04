"""Telegram template flows prepare drafts but never send automatically."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


class Templates:
    def __init__(self): self.items = {}
    def upsert(self, name, text):
        self.items[name] = text
        return {"status": "created", "name": name}
    def list(self): return [{"name": name} for name in self.items]
    def get(self, name):
        return {"name": name, "text": self.items[name]} if name in self.items else None


def test_template_add_and_crm_draft_pending(monkeypatch):
    import run_telegram_bot as bot

    templates = Templates()
    monkeypatch.setattr(bot, "_followup_templates", lambda: templates)
    monkeypatch.setattr(bot, "_phone_lead_queue", lambda: object())
    api = API()
    chat_id = 8181
    try:
        assert bot._handle_phone_lead_intent(api, chat_id, "добавь шаблон follow-up: приветствие | Добрый день")
        bot._last_phone_crm_tasks[chat_id] = [{"id": "task-1"}]
        command = "подготовь шаблон приветствие по CRM задаче 1 в WhatsApp: Иван"
        assert bot._handle_phone_lead_intent(api, chat_id, command)
        pending = bot._pending_confirm[chat_id]
        assert pending["kind"] == "phone_crm_task_draft"
        assert pending["data"]["text"] == "Добрый день"
    finally:
        bot._last_phone_crm_tasks.pop(chat_id, None)
        bot._pending_confirm.pop(chat_id, None)
