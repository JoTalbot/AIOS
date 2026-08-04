"""Tests for private lead cards rendered by the Telegram intent router."""
from __future__ import annotations


class API:
    def __init__(self):
        self.messages = []

    def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class Queue:
    def __init__(self):
        self.reviewed = []

    def sync(self):
        return {"status": "ok", "added": 0}

    def summary(self):
        return {"status": "ok", "pending": 1, "crm_open": 0}

    def list_pending(self, limit=20, source=""):
        return [{"id": "phone-1", "source": "WhatsApp", "observed_at": "2026-08-04T10:00:00", "status": "pending_review"}]

    def review(self, lead_id):
        self.reviewed.append(lead_id)
        return {"status": "reviewed"}

    def promote_to_crm_task(self, lead_id):
        self.promoted = lead_id
        return {"status": "crm_task_created", "task_id": "task-1"}

    def list_crm_tasks(self, limit=30):
        return [{"id": "task-1", "source": "WhatsApp", "created_at": "2026-08-04T10:00:00", "status": "open"}]

    def complete_crm_task(self, task_id):
        self.completed = task_id
        return {"status": "completed"}


def test_phone_lead_cards_do_not_render_notification_content(monkeypatch):
    import run_telegram_bot as bot

    queue = Queue()
    monkeypatch.setattr(bot, "_phone_lead_queue", lambda: queue)
    api = API()
    chat_id = 808080
    try:
        assert bot._handle_phone_lead_intent(api, chat_id, "лиды WhatsApp телефона")
        text = str(api.messages[-1][0][1])
        assert "Потенциальное новое обращение" in text
        assert "секретный текст" not in text
        assert bot._handle_phone_lead_intent(api, chat_id, "отметь лид 1 обработанным")
        assert queue.reviewed == ["phone-1"]
    finally:
        bot._last_phone_leads.pop(chat_id, None)


def test_promote_phone_lead_to_local_crm_task_needs_confirmation(monkeypatch):
    import run_telegram_bot as bot

    queue = Queue()
    monkeypatch.setattr(bot, "_phone_lead_queue", lambda: queue)
    api = API()
    chat_id = 808182
    try:
        bot._handle_phone_lead_intent(api, chat_id, "лиды телефона")
        assert bot._handle_phone_lead_intent(api, chat_id, "создай CRM задачу для лида 1")
        assert bot._pending_confirm[chat_id]["kind"] == "phone_lead_promote"
        pending = bot._pending_confirm.pop(chat_id)
        assert bot._confirm_phone_pending(api, chat_id, pending["kind"], pending["data"])
        assert queue.promoted == "phone-1"
    finally:
        bot._last_phone_leads.pop(chat_id, None)
        bot._pending_confirm.pop(chat_id, None)


def test_complete_local_crm_followup_needs_confirmation(monkeypatch):
    import run_telegram_bot as bot

    queue = Queue()
    monkeypatch.setattr(bot, "_phone_lead_queue", lambda: queue)
    api = API()
    chat_id = 808183
    try:
        assert bot._handle_phone_lead_intent(api, chat_id, "CRM задачи телефона")
        assert bot._handle_phone_lead_intent(api, chat_id, "закрой CRM задачу 1")
        pending = bot._pending_confirm.pop(chat_id)
        assert pending["kind"] == "phone_crm_task_complete"
        assert bot._confirm_phone_pending(api, chat_id, pending["kind"], pending["data"])
        assert queue.completed == "task-1"
    finally:
        bot._last_phone_crm_tasks.pop(chat_id, None)
        bot._pending_confirm.pop(chat_id, None)


def test_crm_task_can_prepare_but_not_send_messenger_draft(monkeypatch):
    import run_telegram_bot as bot

    queue = Queue()

    class Messenger:
        title = "WhatsApp"
        def __init__(self): self.calls = []
        def open_chat(self, contact, confirm=False):
            self.calls.append(("open", contact, confirm))
            return {"status": "opened"}
        def prepare_draft(self, text, confirm=False):
            self.calls.append(("draft", text, confirm))
            return {"status": "draft_ready", "draft_id": "draft-1"}

    messenger = Messenger()
    monkeypatch.setattr(bot, "_phone_lead_queue", lambda: queue)
    monkeypatch.setattr(bot, "_phone_adapter", lambda app: messenger)
    api = API()
    chat_id = 808184
    try:
        bot._handle_phone_lead_intent(api, chat_id, "CRM задачи телефона")
        command = "подготовь черновик по CRM задаче 1 в WhatsApp: Иван | Привет"
        assert bot._handle_phone_lead_intent(api, chat_id, command)
        pending = bot._pending_confirm.pop(chat_id)
        assert pending["kind"] == "phone_crm_task_draft"
        assert bot._confirm_phone_pending(api, chat_id, pending["kind"], pending["data"])
        assert messenger.calls == [("open", "Иван", True), ("draft", "Привет", True)]
        # Sending remains an independent third step.
        assert bot._pending_confirm[chat_id]["kind"] == "whatsapp_send_draft"
    finally:
        bot._last_phone_crm_tasks.pop(chat_id, None)
        bot._pending_confirm.pop(chat_id, None)
