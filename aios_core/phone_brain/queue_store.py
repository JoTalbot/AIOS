"""Хранилище очереди задач Phone Brain (SQLite, WAL).

Одна очередь на устройство — единственный писатель (воркер демона) исключает
гонки ADB/UI между ботом, таймерами и джобами. Состояние переживает рестарт
демона: running-задачи с истёкшим lease возвращаются в очередь.

Машина состояний задачи:
    queued → running → done | failed | need_confirm | cancelled
                 ↖ defer: running → queued (без сжигания попытки, с defer_limit)
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator

from aios_core.phone_brain.common import iso, parse_iso, utc_now

TERMINAL_STATUSES = ("done", "failed", "cancelled", "need_confirm")
ACTIVE_STATUSES = ("queued", "running")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    deferrals INTEGER NOT NULL DEFAULT 0,
    run_after TEXT NOT NULL,
    lease_until TEXT,
    lease_token TEXT,
    worker TEXT,
    dedup_key TEXT,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_poll ON jobs (status, run_after, priority DESC, id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs (dedup_key) WHERE dedup_key IS NOT NULL;
"""


class JobStore:
    """Потокобезопасная очередь задач поверх SQLite."""

    def __init__(self, path: Path | str, *, retry_base_seconds: int = 20,
                 retry_cap_seconds: int = 900, lease_seconds: int = 180,
                 default_max_attempts: int = 3, retention_days: int = 7,
                 defer_limit: int = 20):
        self.path = Path(path)
        self.retry_base_seconds = max(1, int(retry_base_seconds))
        self.retry_cap_seconds = max(self.retry_base_seconds, int(retry_cap_seconds))
        self.lease_seconds = int(lease_seconds)
        self.default_max_attempts = max(1, int(default_max_attempts))
        self.retention_days = max(1, int(retention_days))
        self.defer_limit = max(1, int(defer_limit))
        with self._db() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=15000")
        try:
            yield conn
            conn.commit()  # пустой снаружи BEGIN — no-op
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------ read

    @staticmethod
    def _row_to_job(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        job = dict(row)
        for field in ("payload", "result"):
            raw = job.get(field)
            if isinstance(raw, str) and raw:
                try:
                    job[field] = json.loads(raw)
                except Exception:
                    job[field] = {}
            elif not raw:
                job[field] = {}
        return job

    def get(self, job_id: int) -> dict | None:
        """Возвращает задачу по id или None."""
        with self._db() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (int(job_id),)).fetchone()
        return self._row_to_job(row)

    def list(self, status: str | None = None, limit: int = 50) -> list[dict]:
        """Список задач (свежие первыми), опционально по статусу."""
        limit = max(1, min(int(limit), 500))
        with self._db() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status=? ORDER BY id DESC LIMIT ?",
                    (str(status), limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [job for job in (self._row_to_job(row) for row in rows) if job]

    def counts(self) -> dict[str, int]:
        """Количество задач по статусам."""
        with self._db() as conn:
            rows = conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
        return {str(row["status"]): int(row["n"]) for row in rows}

    def metrics(self) -> dict:
        """Метрики очереди для API/мониторинга."""
        counts = self.counts()
        with self._db() as conn:
            oldest = conn.execute(
                "SELECT created_at FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        result: dict[str, Any] = {"status": "ok", "counts": counts, "queued": counts.get("queued", 0),
                                  "running": counts.get("running", 0)}
        if oldest:
            created = parse_iso(oldest["created_at"])
            if created:
                result["oldest_queued_age_seconds"] = int((utc_now() - created).total_seconds())
        return result

    # ----------------------------------------------------------------- write

    def enqueue(self, kind: str, payload: dict | None = None, *, priority: int = 50,
                max_attempts: int | None = None, run_at: str | None = None,
                dedup_key: str | None = None) -> dict:
        """Ставит задачу в очередь. При совпадении dedup_key с активной задачей
        возвращает существующую (с флагом duplicate=True), не плодя дублей."""
        kind = str(kind or "").strip()
        if not kind:
            return {"status": "error", "error": "Пустой kind задачи"}
        if payload is not None and not isinstance(payload, dict):
            return {"status": "error", "error": "payload должен быть объектом JSON"}
        dedup_key = str(dedup_key).strip()[:120] if dedup_key else None
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if dedup_key:
                row = conn.execute(
                    f"SELECT * FROM jobs WHERE dedup_key=? AND status IN ({','.join('?' * len(ACTIVE_STATUSES))})",
                    (dedup_key, *ACTIVE_STATUSES)).fetchone()
                if row:
                    job = self._row_to_job(row)
                    job["duplicate"] = True
                    return job
            run_after = str(run_at) if run_at else iso()
            cursor = conn.execute(
                "INSERT INTO jobs (kind, payload, priority, max_attempts, run_after, dedup_key, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (kind, json.dumps(payload or {}, ensure_ascii=False), int(priority),
                 max(1, int(max_attempts or self.default_max_attempts)), run_after, dedup_key, iso()))
            job_id = int(cursor.lastrowid)
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            job = self._row_to_job(row)
            job["status_note"] = "queued"
            return job

    def claim(self, worker: str = "phone-brain") -> dict | None:
        """Берёт следующую задачу в работу (аренда). None — очередь пуста."""
        now = utc_now()
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            # Задачи, исчерпавшие попытки за пределами fail() (напр. после lease-expire)
            conn.execute(
                "UPDATE jobs SET status='failed', finished_at=?, error='attempts exhausted'"
                " WHERE status='queued' AND attempts >= max_attempts", (iso(now),))
            row = conn.execute(
                "SELECT * FROM jobs WHERE status='queued' AND run_after<=?"
                " ORDER BY priority DESC, id ASC LIMIT 1", (iso(now),)).fetchone()
            if row is None:
                return None
            token = secrets.token_hex(8)
            lease_until = iso(now + timedelta(seconds=self.lease_seconds))
            conn.execute(
                "UPDATE jobs SET status='running', started_at=?, attempts=attempts+1,"
                " lease_until=?, lease_token=?, worker=? WHERE id=?",
                (iso(now), lease_until, token, str(worker)[:60], int(row["id"])))
            job = self._row_to_job(conn.execute("SELECT * FROM jobs WHERE id=?", (int(row["id"]),)).fetchone())
        return job

    def _finish(self, conn: sqlite3.Connection, job_id: int, lease_token: str,
                status: str, result: dict | None, error: str | None) -> bool:
        cursor = conn.execute(
            "UPDATE jobs SET status=?, result=?, error=?, finished_at=?, lease_until=NULL,"
            " lease_token=NULL WHERE id=? AND lease_token=? AND status='running'",
            (status, json.dumps(result or {}, ensure_ascii=False),
             (str(error)[:300] if error else None), iso(), int(job_id), str(lease_token)))
        return cursor.rowcount == 1

    def complete(self, job_id: int, lease_token: str, result: dict | None = None) -> bool:
        """Помечает задачу успешно выполненной."""
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            return self._finish(conn, job_id, lease_token, "done", result, None)

    def set_need_confirm(self, job_id: int, lease_token: str, payload: dict) -> bool:
        """Терминальный статус: действие требует явного подтверждения владельца."""
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            return self._finish(conn, job_id, lease_token, "need_confirm", payload, None)

    def fail(self, job_id: int, lease_token: str, error: str, *, retry: bool = True) -> dict:
        """Фиксирует провал. Если попытки не исчерпаны и retry=True — возвращает
        задачу в очередь с экспоненциальным backoff, иначе терминальный failed."""
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (int(job_id),)).fetchone()
            if row is None:
                return {"status": "error", "error": "job not found"}
            attempts = int(row["attempts"])
            max_attempts = int(row["max_attempts"])
            if retry and attempts < max_attempts:
                delay = min(self.retry_cap_seconds, self.retry_base_seconds * (2 ** max(0, attempts - 1)))
                run_after = iso(utc_now() + timedelta(seconds=delay))
                conn.execute(
                    "UPDATE jobs SET status='queued', run_after=?, error=?, lease_until=NULL,"
                    " lease_token=NULL WHERE id=?", (run_after, str(error)[:300], int(job_id)))
                return {"status": "queued", "retried": True, "attempts": attempts,
                        "run_after": run_after, "delay_seconds": delay}
            finished = self._finish(conn, job_id, lease_token, "failed", None, error)
            return {"status": "failed" if finished else "error", "retried": False, "attempts": attempts}

    def defer(self, job_id: int, lease_token: str, *, run_after_seconds: int = 30,
              reason: str = "") -> dict:
        """Откладывает задачу по внешней причине (устройство offline и т.п.).
        Не сжигает попытки, но ограничен defer_limit против вечного цикла."""
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (int(job_id),)).fetchone()
            if row is None:
                return {"status": "error", "error": "job not found"}
            deferrals = int(row["deferrals"]) + 1
            if deferrals > self.defer_limit:
                finished = self._finish(conn, job_id, lease_token, "failed", None,
                                        f"Предусловие не выполнено ({reason or 'deferred'})")
                return {"status": "failed" if finished else "error", "reason": reason}
            run_after = iso(utc_now() + timedelta(seconds=max(1, int(run_after_seconds))))
            conn.execute(
                "UPDATE jobs SET status='queued', attempts=MAX(0, attempts-1), deferrals=?,"
                " run_after=?, lease_until=NULL, lease_token=NULL, error=? WHERE id=?",
                (deferrals, run_after, str(reason)[:300] or None, int(job_id)))
            return {"status": "queued", "deferred": True, "deferrals": deferrals, "run_after": run_after}

    def requeue_expired(self) -> int:
        """Возвращает в очередь running-задачи с истёкшей арендой (падение воркера)."""
        now = iso()
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "UPDATE jobs SET status='queued', lease_until=NULL, lease_token=NULL,"
                " error='lease expired' WHERE status='running' AND lease_until < ?", (now,))
            return int(cursor.rowcount)

    def cancel(self, job_id: int) -> dict:
        """Отменяет задачу, пока она в очереди (running-задачи в этапе 1 не трогаем)."""
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "UPDATE jobs SET status='cancelled', finished_at=? WHERE id=? AND status='queued'",
                (iso(), int(job_id)))
            if cursor.rowcount == 1:
                return {"status": "ok", "id": int(job_id)}
            row = conn.execute("SELECT status FROM jobs WHERE id=?", (int(job_id),)).fetchone()
            if row is None:
                return {"status": "error", "error": "job not found"}
            return {"status": "error", "error": f"Задача уже в статусе {row['status']}"}

    def purge(self, retention_days: int | None = None) -> int:
        """Удаляет старые терминальные задачи (ротация)."""
        days = max(1, int(retention_days or self.retention_days))
        cutoff = iso(utc_now() - timedelta(days=days))
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                f"DELETE FROM jobs WHERE finished_at IS NOT NULL AND finished_at < ?"
                f" AND status IN ({','.join('?' * len(TERMINAL_STATUSES))})",
                (cutoff, *TERMINAL_STATUSES))
            return int(cursor.rowcount)
