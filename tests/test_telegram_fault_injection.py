from __future__ import annotations

import errno
import sqlite3
import threading
import time

from cryptography.fernet import Fernet

from scripts import telegram_colab_canary as canary
from scripts import telegram_queue_backup as backup
from tg_bot.outbox import TelegramOutbox


class NoopAPI:
    def send_message(self, *_args, **_kwargs):
        return {"ok": True, "result": {"message_id": 1}}


def test_sqlite_exclusive_lock_never_creates_duplicate_after_retry(tmp_path):
    path = tmp_path / "outbox.sqlite3"
    outbox = TelegramOutbox(NoopAPI(), path)
    blocker = sqlite3.connect(path, timeout=1)
    blocker.execute("BEGIN EXCLUSIVE")
    errors: list[Exception] = []

    def attempt():
        try:
            outbox.enqueue(dedup_key="lock:1", chat_id=1, text="once")
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=attempt)
    worker.start()
    time.sleep(0.1)
    blocker.rollback()
    blocker.close()
    worker.join(3)
    if errors:
        assert isinstance(errors[0], sqlite3.OperationalError)
        assert outbox.enqueue(dedup_key="lock:1", chat_id=1, text="once")
    assert not outbox.enqueue(dedup_key="lock:1", chat_id=1, text="duplicate")


def test_disk_full_backup_cleans_partial_stage_and_key_copy(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    key = tmp_path / "queue.key"
    key.write_bytes(Fernet.generate_key())
    (data / "telegram_outbox.sqlite3").write_bytes(b"placeholder")
    backups = tmp_path / "backups"
    escrow = tmp_path / "escrow"

    def disk_full(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, "simulated disk full")

    monkeypatch.setattr(backup, "_online_backup", disk_full)
    try:
        backup.create_backup(
            data_dir=data,
            backup_root=backups,
            key_file=key,
            key_backup_root=escrow,
            timestamp="20260812T130000Z",
        )
    except OSError as exc:
        assert exc.errno == errno.ENOSPC
    else:
        raise AssertionError("disk-full injection must fail closed")
    assert not (backups / "20260812T130000Z").exists()
    assert not (backups / ".20260812T130000Z.tmp").exists()
    assert list(escrow.glob("*.key")) == []


def test_delete_failure_is_explicit_and_send_is_not_repeated(tmp_path, monkeypatch):
    import aios_core.llm_balancer as balancer_module
    import tg_bot.api as api_module
    import tg_bot.outbox as outbox_module

    calls = {"send": 0, "delete": 0}

    class FakeBalancer:
        def __init__(self):
            self.last_route = {}

        def chat(self, *_args, **_kwargs):
            self.last_route = {"provider": "colab", "model": "colab/qwen2.5-coder"}
            return "ok"

    class FakeAPI:
        def __init__(self, _token):
            pass

        def delete_message(self, *_args):
            calls["delete"] += 1
            raise TimeoutError("delete timeout")

    class FakeOutbox:
        def __init__(self, *_args):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def enqueue(self, **_kwargs):
            calls["send"] += 1
            return True

        def wait(self, *_args, **_kwargs):
            return {"status": "sent", "telegram_message_id": 7, "attempts": 1}

    monkeypatch.setattr(balancer_module, "LLMBalancer", FakeBalancer)
    monkeypatch.setattr(api_module, "TelegramAPI", FakeAPI)
    monkeypatch.setattr(outbox_module, "TelegramOutbox", FakeOutbox)
    monkeypatch.setattr(canary, "STATE_FILE", tmp_path / "state.json")
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / "telegram_owner_chat_id").write_text("777", encoding="utf-8")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))
    monkeypatch.setenv("AIOS_TELEGRAM_TOKEN", "test-token")
    monkeypatch.setattr(canary, "_colab_mode", lambda: "active")
    result = canary.run_canary(send_telegram=True)
    assert result["telegram"]["status"] == "delete_failed"
    assert result["ok"] is False
    assert calls == {"send": 1, "delete": 3}
