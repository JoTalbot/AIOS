from __future__ import annotations

import sqlite3
import threading
import time

from tg_bot.generation_queue import TelegramGenerationQueue


def test_per_chat_order_and_cross_chat_parallelism(tmp_path):
    first_started = threading.Event()
    release_first = threading.Event()
    other_completed = threading.Event()
    calls: list[tuple[int, str]] = []
    lock = threading.Lock()

    def handler(job: dict) -> bool:
        chat_id = int(job["chat_id"])
        text = str(job["text"])
        if chat_id == 1 and text == "first":
            first_started.set()
            assert release_first.wait(2)
        with lock:
            calls.append((chat_id, text))
        if chat_id == 2:
            other_completed.set()
        return True

    queue = TelegramGenerationQueue(handler, tmp_path / "generation.sqlite3")
    queue.start()
    assert queue.enqueue(dedup_key="llm:1", chat_id=1, text="first")
    assert first_started.wait(1)
    assert queue.enqueue(dedup_key="llm:2", chat_id=1, text="second")
    assert queue.enqueue(dedup_key="llm:3", chat_id=2, text="parallel")

    assert other_completed.wait(1), "another chat must not wait for chat 1"
    assert queue.get("llm:2")["status"] == "pending"
    release_first.set()
    assert queue.wait("llm:1", timeout=2)["status"] == "completed"
    assert queue.wait("llm:2", timeout=2)["status"] == "completed"
    queue.stop()

    chat_one = [text for chat, text in calls if chat == 1]
    assert chat_one == ["first", "second"]
    assert (2, "parallel") in calls


def test_update_dedup_and_payload_encryption(tmp_path):
    handled: list[str] = []
    queue = TelegramGenerationQueue(
        lambda job: handled.append(job["text"]) or True,
        tmp_path / "generation.sqlite3",
    )
    queue.start()
    assert queue.enqueue(dedup_key="llm:42", chat_id=7, text="private payload")
    assert not queue.enqueue(dedup_key="llm:42", chat_id=7, text="duplicate payload")
    assert queue.wait("llm:42", timeout=2)["status"] == "completed"
    queue.stop()

    with sqlite3.connect(queue.db_path) as db:
        stored, encrypted = db.execute(
            "SELECT text, encrypted FROM telegram_generation WHERE dedup_key='llm:42'"
        ).fetchone()
    assert encrypted == 1
    assert "private payload" not in stored
    assert handled == ["private payload"]
    assert queue.db_path.with_suffix(queue.db_path.suffix + ".key").stat().st_mode & 0o777 == 0o600


def test_interrupted_generation_is_replayed_after_restart(tmp_path):
    db_path = tmp_path / "generation.sqlite3"
    dormant = TelegramGenerationQueue(lambda _job: True, db_path)
    dormant.stop()
    assert dormant.enqueue(dedup_key="llm:restart", chat_id=11, text="resume me")
    with sqlite3.connect(db_path) as db:
        db.execute(
            "UPDATE telegram_generation SET status='generating', worker_pid=?, lease_until=? "
            "WHERE dedup_key='llm:restart'",
            (99999999, time.time() - 1),
        )

    handled: list[str] = []
    restarted = TelegramGenerationQueue(
        lambda job: handled.append(job["text"]) or True,
        db_path,
    )
    restarted.start()
    row = restarted.wait("llm:restart", timeout=2)
    restarted.stop()

    assert row["status"] == "completed"
    assert row["attempts"] == 1
    assert handled == ["resume me"]


def test_failed_generation_has_bounded_retries(tmp_path):
    calls = 0

    def fail(_job: dict) -> bool:
        nonlocal calls
        calls += 1
        raise TimeoutError("temporary")

    queue = TelegramGenerationQueue(fail, tmp_path / "generation.sqlite3", max_attempts=2)
    queue.start()
    assert queue.enqueue(dedup_key="llm:fail", chat_id=9, text="retry")
    row = queue.wait("llm:fail", timeout=2)
    queue.stop()

    assert row["status"] == "dead_letter"
    assert row["attempts"] == 2
    assert row["error_class"] == "TimeoutError"
    assert queue.list_dead_letters()[0]["dedup_key"] == "llm:fail"
    assert calls == 2


def test_two_process_views_cannot_generate_same_chat_out_of_order(tmp_path):
    db_path = tmp_path / "generation.sqlite3"
    first = TelegramGenerationQueue(lambda _job: True, db_path)
    first.stop()
    assert first.enqueue(dedup_key="llm:a", chat_id=5, text="a")
    assert first.enqueue(dedup_key="llm:b", chat_id=5, text="b")
    claimed = first._claim(5)
    assert claimed is not None and claimed["dedup_key"] == "llm:a"

    second = TelegramGenerationQueue(lambda _job: True, db_path)
    second.stop()
    assert second._claim(5) is None


def test_generation_lease_is_renewed_during_long_handler(tmp_path):
    started = threading.Event()
    release = threading.Event()

    def slow(_job: dict) -> bool:
        started.set()
        assert release.wait(3)
        return True

    db = tmp_path / "generation.sqlite3"
    queue = TelegramGenerationQueue(slow, db, lease_seconds=2)
    queue.start()
    assert queue.enqueue(dedup_key="llm:lease", chat_id=1, text="slow")
    assert started.wait(1)
    first_lease = queue.get("llm:lease")["lease_until"]
    time.sleep(1.2)
    second_lease = queue.get("llm:lease")["lease_until"]
    assert second_lease > first_lease

    competing = TelegramGenerationQueue(lambda _job: True, db, lease_seconds=2)
    competing.stop()
    assert competing._claim(1) is None
    release.set()
    assert queue.wait("llm:lease", timeout=2)["status"] == "completed"
    queue.stop()


def test_dead_letter_can_be_explicitly_requeued(tmp_path):
    calls = 0

    def recover(_job: dict) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("poison")
        return True

    queue = TelegramGenerationQueue(
        recover, tmp_path / "generation.sqlite3", max_attempts=1
    )
    queue.start()
    assert queue.enqueue(dedup_key="llm:dead", chat_id=3, text="retry explicitly")
    dead = queue.wait("llm:dead", timeout=2)
    assert dead["status"] == "dead_letter"
    assert queue.requeue_dead_letter(dead["id"])
    assert queue.wait("llm:dead", timeout=2)["status"] == "completed"
    queue.stop()


def test_graceful_drain_finishes_durable_jobs_and_rejects_new(tmp_path):
    release = threading.Event()

    def slow(_job: dict) -> bool:
        assert release.wait(2)
        return True

    queue = TelegramGenerationQueue(slow, tmp_path / "generation.sqlite3")
    queue.start()
    assert queue.enqueue(dedup_key="llm:drain", chat_id=4, text="finish me")
    done: list[bool] = []
    thread = threading.Thread(target=lambda: done.append(queue.stop(2, drain=True)))
    thread.start()
    time.sleep(0.1)
    from tg_bot.generation_queue import QueueDrainingError

    try:
        queue.enqueue(dedup_key="llm:new", chat_id=4, text="reject me")
    except QueueDrainingError:
        pass
    else:
        raise AssertionError("new work must be rejected during drain")
    release.set()
    thread.join(3)
    assert done == [True]
    assert queue.get("llm:drain")["status"] == "completed"
