"""Persistent at-most-once Telegram outbound queue.

Telegram Bot API has no idempotency key.  Retrying a ``sendMessage`` after a
read timeout can therefore create duplicates: Telegram may have accepted the
first request even though the client never received its response.  This queue
marks an item as ``sending`` *before* the network call and never automatically
retries an ambiguous failure.  A process restart converts stale ``sending``
rows to ``failed_unknown`` rather than delivering them again.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable

OnSent = Callable[[dict], None]


class TelegramOutbox:
    def __init__(self, api: Any, db_path: str | Path | None = None) -> None:
        self.api = api
        self.db_path = Path(
            db_path
            or os.environ.get("TELEGRAM_OUTBOX_DB", "")
            or Path(__file__).resolve().parents[1] / "data" / "telegram_outbox.sqlite3"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._callbacks: dict[int, OnSent] = {}
        self._callbacks_lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        for path in (
            self.db_path,
            Path(str(self.db_path) + "-wal"),
            Path(str(self.db_path) + "-shm"),
        ):
            if path.exists():
                os.chmod(path, 0o600)
        return connection

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedup_key TEXT NOT NULL UNIQUE,
                    chat_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    parse_mode TEXT NOT NULL DEFAULT '',
                    reply_markup_json TEXT,
                    generation_sec REAL NOT NULL DEFAULT 0,
                    provider TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    telegram_message_id INTEGER,
                    error_class TEXT NOT NULL DEFAULT '',
                    worker_pid INTEGER,
                    lease_until REAL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL
                )
                """
            )
            # Lightweight migration for databases created before worker leases.
            columns = {row[1] for row in db.execute("PRAGMA table_info(telegram_outbox)")}
            if "worker_pid" not in columns:
                db.execute("ALTER TABLE telegram_outbox ADD COLUMN worker_pid INTEGER")
            if "lease_until" not in columns:
                db.execute("ALTER TABLE telegram_outbox ADD COLUMN lease_until REAL")

            # A second process (for example the canary) must not invalidate the
            # bot's active send. Fail closed only when the owner process is gone
            # or its bounded network lease has expired.
            now = time.time()
            for row in db.execute(
                "SELECT id, worker_pid, lease_until FROM telegram_outbox WHERE status='sending'"
            ).fetchall():
                pid = int(row["worker_pid"] or 0)
                lease_until = float(row["lease_until"] or 0)
                owner_alive = pid > 0 and Path(f"/proc/{pid}").exists()
                if not owner_alive or lease_until < now:
                    db.execute(
                        """
                        UPDATE telegram_outbox
                        SET status='failed_unknown', error_class='process_interrupted', finished_at=?
                        WHERE id=? AND status='sending'
                        """,
                        (now, row["id"]),
                    )
            db.execute(
                "DELETE FROM telegram_outbox WHERE created_at < ? AND status IN ('sent','failed','failed_unknown')",
                (time.time() - 30 * 86400,),
            )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="telegram-outbox", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def seen(self, dedup_key: str) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM telegram_outbox WHERE dedup_key=? LIMIT 1", (dedup_key,)
            ).fetchone()
        return row is not None

    def enqueue(
        self,
        *,
        dedup_key: str,
        chat_id: int,
        text: str,
        parse_mode: str = "",
        reply_markup: dict | None = None,
        generation_sec: float = 0.0,
        provider: str = "",
        model: str = "",
        on_sent: OnSent | None = None,
    ) -> bool:
        """Persist one message. Return ``False`` when its dedup key already exists."""
        if not dedup_key or not text:
            raise ValueError("dedup_key and text are required")
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO telegram_outbox (
                    dedup_key, chat_id, text, parse_mode, reply_markup_json,
                    generation_sec, provider, model, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    dedup_key,
                    int(chat_id),
                    text,
                    parse_mode,
                    json.dumps(reply_markup, ensure_ascii=False) if reply_markup else None,
                    max(0.0, float(generation_sec)),
                    provider,
                    model,
                    time.time(),
                ),
            )
            inserted = cursor.rowcount == 1
            item_id = int(cursor.lastrowid) if inserted else 0
        if inserted and on_sent:
            with self._callbacks_lock:
                self._callbacks[item_id] = on_sent
        if inserted:
            self._wake.set()
        return inserted

    def get(self, dedup_key: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM telegram_outbox WHERE dedup_key=?", (dedup_key,)
            ).fetchone()
        return dict(row) if row else None

    def wait(self, dedup_key: str, timeout: float = 10.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            row = self.get(dedup_key)
            if row and row["status"] not in ("pending", "sending"):
                return row
            time.sleep(0.02)
        return self.get(dedup_key)

    def _claim_next(self) -> sqlite3.Row | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM telegram_outbox WHERE status='pending' ORDER BY id LIMIT 1"
            ).fetchone()
            if not row:
                db.commit()
                return None
            updated = db.execute(
                """
                UPDATE telegram_outbox
                SET status='sending', attempts=attempts+1, started_at=?,
                    worker_pid=?, lease_until=?
                WHERE id=? AND status='pending'
                """,
                (time.time(), os.getpid(), time.time() + 60, row["id"]),
            ).rowcount
            db.commit()
            return row if updated == 1 else None

    def _finish(
        self,
        item_id: int,
        *,
        status: str,
        telegram_message_id: int | None = None,
        error_class: str = "",
    ) -> None:
        with self._connect() as db:
            db.execute(
                """
                UPDATE telegram_outbox
                SET status=?, telegram_message_id=?, error_class=?, finished_at=?,
                    worker_pid=NULL, lease_until=NULL
                WHERE id=?
                """,
                (status, telegram_message_id, error_class, time.time(), item_id),
            )

    def _record_metric(self, event: dict) -> None:
        try:
            from tg_bot.metrics import record_telegram_event

            record_telegram_event(event)
        except Exception:
            pass

    def _worker(self) -> None:
        while not self._stop.is_set():
            row = self._claim_next()
            if row is None:
                self._wake.clear()
                self._wake.wait(timeout=1.0)
                continue

            send_started = time.monotonic()
            status = "failed_unknown"
            error_class = ""
            telegram_message_id = None
            result: dict = {}
            try:
                reply_markup = json.loads(row["reply_markup_json"]) if row["reply_markup_json"] else None
                result = self.api.send_message(
                    int(row["chat_id"]),
                    str(row["text"]),
                    parse_mode=str(row["parse_mode"]),
                    reply_markup=reply_markup,
                )
                telegram_message_id = result.get("result", {}).get("message_id")
                status = "sent"
            except Exception as exc:
                # No retry: a timeout after server acceptance is indistinguishable
                # from a failed request and replaying can duplicate the reply.
                error_class = type(exc).__name__
            send_sec = time.monotonic() - send_started
            self._finish(
                int(row["id"]),
                status=status,
                telegram_message_id=telegram_message_id,
                error_class=error_class,
            )
            total_sec = float(row["generation_sec"]) + send_sec
            event = {
                "event": "telegram_send",
                "status": status,
                "dedup_key": row["dedup_key"],
                "provider": row["provider"],
                "model": row["model"],
                "gen_sec": round(float(row["generation_sec"]), 3),
                "send_sec": round(send_sec, 3),
                "total_sec": round(total_sec, 3),
                "attempts": int(row["attempts"]) + 1,
                "error_class": error_class,
                "timestamp": time.time(),
            }
            self._record_metric(event)
            if status == "sent":
                print(
                    f"  -> LLM sent (provider={row['provider'] or 'unknown'}, "
                    f"model={row['model'] or 'unknown'}, gen={float(row['generation_sec']):.2f}s, "
                    f"send={send_sec:.2f}s, total={total_sec:.2f}s, status=sent)"
                )
                callback = None
                with self._callbacks_lock:
                    callback = self._callbacks.pop(int(row["id"]), None)
                if callback:
                    try:
                        callback(result)
                    except Exception as exc:
                        print(f"  [VOICE] post-send callback failed: {type(exc).__name__}")
            else:
                with self._callbacks_lock:
                    self._callbacks.pop(int(row["id"]), None)
                print(
                    f"  [ERR] LLM send status={status}, error={error_class}, "
                    f"gen={float(row['generation_sec']):.2f}s, send={send_sec:.2f}s, total={total_sec:.2f}s"
                )
