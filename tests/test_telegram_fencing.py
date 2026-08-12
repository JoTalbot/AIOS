from __future__ import annotations

import sqlite3

from tg_bot.generation_queue import TelegramGenerationQueue
from tg_bot.outbox import TelegramOutbox


class NoopAPI:
    def send_message(self, *_args, **_kwargs):
        return {"ok": True, "result": {"message_id": 1}}


def test_generation_stale_epoch_cannot_finish_reassigned_job(tmp_path):
    path = tmp_path / "generation.sqlite3"
    first = TelegramGenerationQueue(lambda _job: True, path)
    first.stop()
    assert first.enqueue(dedup_key="lease:fence", chat_id=1, text="payload")
    old = first._claim(1)
    assert old is not None

    # Simulate expiry/recovery and assignment to another worker generation.
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE telegram_generation SET status='pending', worker_pid=NULL, "
            "worker_id=NULL, lease_until=NULL WHERE id=?",
            (old["id"],),
        )
    second = TelegramGenerationQueue(lambda _job: True, path)
    second.stop()
    current = second._claim(1)
    assert current is not None
    assert current["lease_epoch"] > old["lease_epoch"]

    assert not first._finish(old["id"], old["lease_epoch"], status="completed")
    row = second.get("lease:fence")
    assert row["status"] == "generating"
    assert row["lease_epoch"] == current["lease_epoch"]
    assert second._finish(current["id"], current["lease_epoch"], status="completed")


def test_outbox_stale_epoch_cannot_overwrite_ambiguous_reassignment(tmp_path):
    path = tmp_path / "outbox.sqlite3"
    first = TelegramOutbox(NoopAPI(), path)
    assert first.enqueue(dedup_key="send:fence", chat_id=1, text="payload")
    old = first._claim_next()
    assert old is not None

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE telegram_outbox SET status='pending', worker_pid=NULL, "
            "worker_id=NULL, lease_until=NULL WHERE id=?",
            (old["id"],),
        )
    second = TelegramOutbox(NoopAPI(), path)
    current = second._claim_next()
    assert current is not None
    assert current["lease_epoch"] > old["lease_epoch"]

    assert not first._finish(old["id"], old["lease_epoch"], status="sent")
    row = second.get("send:fence")
    assert row["status"] == "sending"
    assert row["lease_epoch"] == current["lease_epoch"]
    assert second._finish(current["id"], current["lease_epoch"], status="failed_unknown")
