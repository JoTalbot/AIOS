"""Тесты очереди Viber-черновиков и запрета неявной отправки."""
from __future__ import annotations

from aios_core.autonomy.executor import Executor
from viber_drafts import ViberDraftStore


def test_viber_draft_queue_is_idempotent_and_claimable(tmp_path):
    store = ViberDraftStore(tmp_path)
    first, created = store.enqueue("Чат", "Привет!", "Исходное сообщение")
    assert created is True
    same, created_again = store.enqueue("Чат", "Другой текст", "Исходное сообщение")
    assert created_again is False
    assert same["id"] == first["id"]
    assert len(store.pending()) == 1

    claimed = store.claim(first["id"])
    assert claimed and claimed["status"] == "sending"
    assert store.claim(first["id"]) is None
    finalized = store.finalize(first["id"], sent=False, error="temporary")
    assert finalized and finalized["status"] == "pending"
    cancelled = store.cancel(first["id"])
    assert cancelled and cancelled["status"] == "cancelled"
    assert store.pending() == []


def test_autonomy_viber_reply_returns_draft_not_real_send(tmp_path):
    result = Executor(tmp_path).execute({
        "action": "reply_customer",
        "params": {"text": "Здравствуйте, товар в наличии."},
        "platform": "viber",
        "chat": "Тестовый чат",
    })
    assert result["status"] == "draft"
    assert result["draft_text"] == "Здравствуйте, товар в наличии."
