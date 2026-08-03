"""Тесты очереди Signal-черновиков и запрета неявной отправки."""
from __future__ import annotations

from aios_core.autonomy.executor import Executor
from signal_drafts import SignalDraftStore


def test_signal_draft_queue_is_idempotent_and_claimable(tmp_path):
    store = SignalDraftStore(tmp_path)
    first, created = store.enqueue("Чат", "Привет!", "Исходное сообщение")
    assert created is True
    same, created_again = store.enqueue("Чат", "Другой текст", "Исходное сообщение")
    assert created_again is False
    assert same["id"] == first["id"]

    claimed = store.claim(first["id"])
    assert claimed and claimed["status"] == "sending"
    assert store.claim(first["id"]) is None
    assert store.finalize(first["id"], sent=False, error="temporary")["status"] == "pending"
    assert store.cancel(first["id"])["status"] == "cancelled"


def test_autonomy_signal_reply_returns_draft_not_real_send(tmp_path):
    result = Executor(tmp_path).execute({
        "action": "reply_customer",
        "params": {"text": "Здравствуйте, сообщение получил."},
        "platform": "signal",
        "chat": "Тестовый чат",
    })
    assert result["status"] == "draft"
    assert result["draft_text"] == "Здравствуйте, сообщение получил."
