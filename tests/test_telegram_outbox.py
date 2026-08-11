from __future__ import annotations

import json
import sqlite3
import threading
import time

from tg_bot.metrics import record_telegram_event, summarize_telegram_metrics
from tg_bot.outbox import TelegramOutbox


class FakeAPI:
    def __init__(self, *, error: Exception | None = None, delay: float = 0.0):
        self.error = error
        self.delay = delay
        self.calls = []
        self.started = threading.Event()

    def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None):
        self.calls.append((chat_id, text, parse_mode, reply_markup))
        self.started.set()
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return {"ok": True, "result": {"message_id": 123}}


def test_outbox_enqueues_without_waiting_for_slow_send(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    api = FakeAPI(delay=0.2)
    outbox = TelegramOutbox(api, tmp_path / "outbox.sqlite3")
    outbox.start()
    started = time.monotonic()
    assert outbox.enqueue(dedup_key="llm:1", chat_id=7, text="hello")
    enqueue_sec = time.monotonic() - started
    assert enqueue_sec < 0.1
    assert api.started.wait(1)
    row = outbox.wait("llm:1", timeout=2)
    outbox.stop()
    assert row["status"] == "sent"
    assert row["attempts"] == 1
    assert api.calls == [(7, "hello", "", None)]


def test_duplicate_update_is_sent_once(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    api = FakeAPI()
    outbox = TelegramOutbox(api, tmp_path / "outbox.sqlite3")
    assert outbox.enqueue(dedup_key="llm:42", chat_id=7, text="one")
    assert not outbox.enqueue(dedup_key="llm:42", chat_id=7, text="two")
    outbox.start()
    assert outbox.wait("llm:42", timeout=2)["status"] == "sent"
    outbox.stop()
    assert len(api.calls) == 1
    assert api.calls[0][1] == "one"


def test_ambiguous_timeout_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    api = FakeAPI(error=TimeoutError("ambiguous read timeout"))
    db = tmp_path / "outbox.sqlite3"
    outbox = TelegramOutbox(api, db)
    outbox.start()
    assert outbox.enqueue(dedup_key="llm:9", chat_id=7, text="once")
    row = outbox.wait("llm:9", timeout=2)
    outbox.stop()
    assert row["status"] == "failed_unknown"
    assert row["attempts"] == 1

    restarted = TelegramOutbox(api, db)
    restarted.start()
    time.sleep(0.1)
    restarted.stop()
    assert len(api.calls) == 1


def test_second_process_view_does_not_invalidate_live_send(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    api = FakeAPI(delay=0.2)
    db = tmp_path / "outbox.sqlite3"
    first = TelegramOutbox(api, db)
    first.start()
    assert first.enqueue(dedup_key="llm:live", chat_id=7, text="live")
    assert api.started.wait(1)
    second = TelegramOutbox(api, db)
    assert second.get("llm:live")["status"] == "sending"
    assert first.wait("llm:live", timeout=2)["status"] == "sent"
    first.stop()
    assert len(api.calls) == 1


def test_interrupted_sending_row_is_failed_closed_on_startup(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    api = FakeAPI()
    db = tmp_path / "outbox.sqlite3"
    outbox = TelegramOutbox(api, db)
    assert outbox.enqueue(dedup_key="llm:10", chat_id=7, text="uncertain")
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE telegram_outbox SET status='sending' WHERE dedup_key='llm:10'")
    restarted = TelegramOutbox(api, db)
    assert restarted.get("llm:10")["status"] == "failed_unknown"
    restarted.start()
    time.sleep(0.1)
    restarted.stop()
    assert api.calls == []


def test_structured_metrics_have_percentiles_without_content(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "1")
    path = tmp_path / "metrics.jsonl"
    now = time.time()
    for index, value in enumerate((0.1, 0.2, 0.5)):
        record_telegram_event(
            {
                "event": "telegram_send",
                "status": "sent",
                "provider": "colab",
                "model": "colab/qwen2.5-coder",
                "gen_sec": value,
                "send_sec": value,
                "total_sec": value * 2,
                "timestamp": now + index / 100,
                "text": "must not be stored",
            },
            path=path,
        )
    summary = summarize_telegram_metrics(hours=1, path=path)
    assert summary["events"] == 3
    assert summary["providers"] == {"colab": 3}
    assert summary["latency"]["send_p95"] == 0.5
    assert "must not be stored" not in path.read_text(encoding="utf-8")


def test_legacy_plaintext_is_encrypted_in_place(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    db = tmp_path / "outbox.sqlite3"
    original = TelegramOutbox(FakeAPI(), db)
    with sqlite3.connect(db) as connection:
        connection.execute(
            """
            INSERT INTO telegram_outbox (
                dedup_key, chat_id, text, encrypted, parse_mode, status, created_at
            ) VALUES ('legacy:1', 7, 'legacy private text', 0, '', 'pending', ?)
            """,
            (time.time(),),
        )

    api = FakeAPI()
    migrated = TelegramOutbox(api, db)
    with sqlite3.connect(db) as connection:
        stored, encrypted = connection.execute(
            "SELECT text, encrypted FROM telegram_outbox WHERE dedup_key='legacy:1'"
        ).fetchone()
    assert encrypted == 1
    assert "legacy private text" not in stored

    migrated.start()
    assert migrated.wait("legacy:1", timeout=2)["status"] == "sent"
    migrated.stop()
    assert api.calls[0][1] == "legacy private text"


def test_manual_resend_is_atomic_and_only_for_failed_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    api = FakeAPI(error=TimeoutError("ambiguous"))
    outbox = TelegramOutbox(api, tmp_path / "outbox.sqlite3")
    outbox.start()
    assert outbox.enqueue(dedup_key="llm:uncertain", chat_id=7, text="once")
    uncertain = outbox.wait("llm:uncertain", timeout=2)
    assert uncertain["status"] == "failed_unknown"
    assert outbox.manual_resend(uncertain["id"])
    assert not outbox.manual_resend(uncertain["id"])
    deadline = time.monotonic() + 2
    while len(api.calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.02)
    outbox.stop()

    assert outbox.get("llm:uncertain")["status"] == "resend_queued"
    remaining = outbox.list_uncertain()
    assert len(remaining) == 1
    assert remaining[0]["dedup_key"].startswith("manual-resend:")
    assert len(api.calls) == 2


def test_definitive_api_rejection_is_not_failed_unknown(tmp_path, monkeypatch):
    from tg_bot.api import TelegramAPIError

    monkeypatch.setenv("TELEGRAM_METRICS_ENABLED", "0")
    outbox = TelegramOutbox(
        FakeAPI(error=TelegramAPIError("rejected")), tmp_path / "outbox.sqlite3"
    )
    outbox.start()
    assert outbox.enqueue(dedup_key="llm:bad", chat_id=7, text="bad")
    row = outbox.wait("llm:bad", timeout=2)
    outbox.stop()
    assert row["status"] == "failed"
    assert outbox.list_uncertain() == []
