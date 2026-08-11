"""Durable per-chat LLM generation scheduler.

Polling only persists an inbound job and immediately returns to ``getUpdates``.
Each chat has one sequential worker, while different chats can generate in
parallel.  Crashed ``generating`` jobs are replayed safely because the outbound
queue owns the final update-id deduplication key.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable

from tg_bot.crypto_store import QueueCipher

GenerationHandler = Callable[[dict], bool]


class TelegramGenerationQueue:
    def __init__(
        self,
        handler: GenerationHandler,
        db_path: str | Path | None = None,
        *,
        max_attempts: int = 2,
    ) -> None:
        self.handler = handler
        self.db_path = Path(
            db_path
            or os.environ.get("TELEGRAM_GENERATION_DB", "")
            or Path(__file__).resolve().parents[1] / "data" / "telegram_generation.sqlite3"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        key_path = (
            self.db_path.with_suffix(self.db_path.suffix + ".key")
            if db_path is not None
            else Path(__file__).resolve().parents[1] / "data" / "credentials" / "telegram_queue.key"
        )
        self._cipher = QueueCipher(os.environ.get("TELEGRAM_QUEUE_KEY_FILE", "") or key_path)
        self.max_attempts = max(1, int(max_attempts))
        self._stop = threading.Event()
        self._workers: dict[int, threading.Thread] = {}
        self._workers_lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        for path in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            if path.exists():
                os.chmod(path, 0o600)
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_generation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedup_key TEXT NOT NULL UNIQUE,
                    chat_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    encrypted INTEGER NOT NULL DEFAULT 1,
                    source_message_id INTEGER,
                    voice_reply INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error_class TEXT NOT NULL DEFAULT '',
                    worker_pid INTEGER,
                    lease_until REAL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL
                )
                """
            )
            now = time.time()
            rows = db.execute(
                "SELECT id, worker_pid, lease_until FROM telegram_generation WHERE status='generating'"
            ).fetchall()
            for row in rows:
                pid = int(row["worker_pid"] or 0)
                alive = pid > 0 and Path(f"/proc/{pid}").exists()
                if not alive or float(row["lease_until"] or 0) < now:
                    db.execute(
                        """
                        UPDATE telegram_generation
                        SET status='pending', worker_pid=NULL, lease_until=NULL,
                            error_class='process_interrupted'
                        WHERE id=? AND status='generating'
                        """,
                        (row["id"],),
                    )
            retention_days = max(
                1, int(os.environ.get("TELEGRAM_GENERATION_RETENTION_DAYS", "14"))
            )
            db.execute(
                "DELETE FROM telegram_generation WHERE created_at < ? AND status IN ('completed','failed')",
                (now - retention_days * 86400,),
            )

    def start(self) -> None:
        self._stop.clear()
        with self._connect() as db:
            chats = [int(row[0]) for row in db.execute(
                "SELECT DISTINCT chat_id FROM telegram_generation WHERE status='pending'"
            )]
        for chat_id in chats:
            self._ensure_worker(chat_id)

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        with self._workers_lock:
            workers = list(self._workers.values())
        deadline = time.monotonic() + timeout
        for worker in workers:
            worker.join(timeout=max(0.0, deadline - time.monotonic()))

    def enqueue(
        self,
        *,
        dedup_key: str,
        chat_id: int,
        text: str,
        source_message_id: int | None = None,
        voice_reply: bool = False,
    ) -> bool:
        if not dedup_key or not text:
            raise ValueError("dedup_key and text are required")
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO telegram_generation (
                    dedup_key, chat_id, text, encrypted, source_message_id,
                    voice_reply, status, created_at
                ) VALUES (?, ?, ?, 1, ?, ?, 'pending', ?)
                """,
                (
                    dedup_key,
                    int(chat_id),
                    self._cipher.encrypt(text),
                    source_message_id,
                    1 if voice_reply else 0,
                    time.time(),
                ),
            )
            inserted = cursor.rowcount == 1
        if inserted:
            self._ensure_worker(int(chat_id))
        return inserted

    def seen(self, dedup_key: str) -> bool:
        return self.get(dedup_key) is not None

    def get(self, dedup_key: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM telegram_generation WHERE dedup_key=?", (dedup_key,)
            ).fetchone()
        return dict(row) if row else None

    def wait(self, dedup_key: str, timeout: float = 10.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            row = self.get(dedup_key)
            if row and row["status"] not in ("pending", "generating"):
                return row
            time.sleep(0.02)
        return self.get(dedup_key)

    def _ensure_worker(self, chat_id: int) -> None:
        with self._workers_lock:
            current = self._workers.get(chat_id)
            if current and current.is_alive():
                return
            worker = threading.Thread(
                target=self._chat_worker,
                args=(chat_id,),
                name=f"telegram-generation-{chat_id}",
                daemon=True,
            )
            self._workers[chat_id] = worker
            worker.start()

    def _claim(self, chat_id: int) -> sqlite3.Row | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """
                SELECT * FROM telegram_generation AS candidate
                WHERE candidate.chat_id=? AND candidate.status='pending'
                  AND NOT EXISTS (
                      SELECT 1 FROM telegram_generation AS active
                      WHERE active.chat_id=candidate.chat_id AND active.status='generating'
                  )
                ORDER BY candidate.id LIMIT 1
                """,
                (chat_id,),
            ).fetchone()
            if not row:
                db.commit()
                return None
            changed = db.execute(
                """
                UPDATE telegram_generation
                SET status='generating', attempts=attempts+1, started_at=?,
                    worker_pid=?, lease_until=?
                WHERE id=? AND status='pending'
                """,
                (time.time(), os.getpid(), time.time() + 900, row["id"]),
            ).rowcount
            db.commit()
            return row if changed == 1 else None

    def _finish(self, item_id: int, *, status: str, error_class: str = "") -> None:
        with self._connect() as db:
            db.execute(
                """
                UPDATE telegram_generation
                SET status=?, error_class=?, worker_pid=NULL, lease_until=NULL,
                    finished_at=?
                WHERE id=?
                """,
                (status, error_class, time.time(), item_id),
            )

    def _retry_or_fail(self, row: sqlite3.Row, error_class: str) -> None:
        attempts_after_claim = int(row["attempts"]) + 1
        status = "pending" if attempts_after_claim < self.max_attempts else "failed"
        with self._connect() as db:
            db.execute(
                """
                UPDATE telegram_generation
                SET status=?, error_class=?, worker_pid=NULL, lease_until=NULL,
                    finished_at=CASE WHEN ?='failed' THEN ? ELSE NULL END
                WHERE id=?
                """,
                (status, error_class, status, time.time(), row["id"]),
            )

    def _chat_worker(self, chat_id: int) -> None:
        try:
            while not self._stop.is_set():
                row = self._claim(chat_id)
                if row is None:
                    return
                job = dict(row)
                try:
                    job["text"] = self._cipher.decrypt(
                        str(row["text"]), encrypted=bool(row["encrypted"])
                    )
                    completed = bool(self.handler(job))
                    if completed:
                        self._finish(int(row["id"]), status="completed")
                    else:
                        self._retry_or_fail(row, "handler_incomplete")
                except Exception as exc:
                    self._retry_or_fail(row, type(exc).__name__)
                    print(
                        f"  [LLM] generation job failed ({row['dedup_key']}): "
                        f"{type(exc).__name__}"
                    )
        finally:
            with self._workers_lock:
                current = self._workers.get(chat_id)
                if current is threading.current_thread():
                    self._workers.pop(chat_id, None)
            # Close the enqueue/worker-exit race.
            if not self._stop.is_set():
                with self._connect() as db:
                    pending = db.execute(
                        "SELECT 1 FROM telegram_generation WHERE chat_id=? AND status='pending' LIMIT 1",
                        (chat_id,),
                    ).fetchone()
                if pending:
                    self._ensure_worker(chat_id)
