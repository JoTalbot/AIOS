"""ShardExec — pull-модель джобов на шардированных нодах.

Альтернатива crontab: оператор вешает джобу (`enqueue`) на профиль,
ноды сами забирают (`claim`) джобы, чей sticky HRW-маршрут указывает
на них (та же ``AIOS_SHARDS_DB``, что и :class:`ShardRouter`). Джоба
профиля никогда не уедет на чужую ноду, пока маршрут жив — двойного
запуска autopilot-цикла на двух хостах не бывает.

`ShardJobWorker` исполняет джобы через инъецируемые обработчики
(kind → callable), CLI `aios shards work --once` — с дефолтным
реестром встроенных видов (autopilot — shell-out в aios_cli).
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shard_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    host TEXT,
    enqueued_at TEXT NOT NULL,
    claimed_at TEXT,
    finished_at TEXT,
    result TEXT
);
CREATE INDEX IF NOT EXISTS idx_shard_jobs_status ON shard_jobs(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShardJobs:
    """Очередь джобов профилей поверх shard-базы (AIOS_SHARDS_DB).

    Args:
        db_path: путь к sqlite shard-базы; None → env ``AIOS_SHARDS_DB``
            или ``:memory:``.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("AIOS_SHARDS_DB", ":memory:")
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def __enter__(self) -> "ShardJobs":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # -- очередь ------------------------------------------------------

    def enqueue(
        self, profile_key: str, kind: str, payload: Optional[Dict] = None
    ) -> int:
        """Повесить джобу на профиль; вернуть id."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO shard_jobs (profile_key, kind, payload, enqueued_at)"
                " VALUES (?, ?, ?, ?)",
                (
                    profile_key, kind,
                    json.dumps(payload or {}, ensure_ascii=False), _now(),
                ),
            )
            return int(cursor.lastrowid)

    def _row(self, row) -> Dict:
        item = dict(row)
        item["payload"] = json.loads(item["payload"] or "{}")
        if item.get("result") is not None:
            try:
                item["result"] = json.loads(item["result"])
            except (TypeError, ValueError):
                pass
        return item

    def list(self, status: Optional[str] = None) -> List[Dict]:
        """Джобы по статусу (None — все), старые первыми."""
        sql = "SELECT * FROM shard_jobs"
        params: list = []
        if status is not None:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row(row) for row in rows]

    def _host_for(self, profile_key: str) -> Optional[str]:
        """Sticky-хост маршрута профиля (та же shard-база)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT r.host FROM shard_routes r "
                "JOIN shard_hosts h ON h.host = r.host "
                "WHERE r.profile_key = ? AND h.healthy = 1",
                (profile_key,),
            ).fetchone()
        return row["host"] if row else None

    def pending_for(self, host: str) -> List[Dict]:
        """Pending-джобы, маршрут которых указывает на ``host``."""
        return [
            job for job in self.list(status="pending")
            if self._host_for(job["profile_key"]) == host
        ]

    def claim_next(self, host: str) -> Optional[Dict]:
        """Атомарно забрать следующую джобу ноды (статуc → claimed)."""
        with self._lock, self._conn:
            for job in self.pending_for(host):
                cursor = self._conn.execute(
                    "UPDATE shard_jobs SET status = 'claimed', host = ?, "
                    "claimed_at = ? WHERE id = ? AND status = 'pending'",
                    (host, _now(), job["id"]),
                )
                if cursor.rowcount:
                    job["status"] = "claimed"
                    job["host"] = host
                    return job
        return None

    def complete(
        self, job_id: int, ok: bool = True, result: Optional[Dict] = None
    ) -> bool:
        """Зафиксировать результат джобы (done/failed)."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE shard_jobs SET status = ?, finished_at = ?, result = ? "
                "WHERE id = ?",
                (
                    "done" if ok else "failed", _now(),
                    json.dumps(result or {}, ensure_ascii=False), job_id,
                ),
            )
            return bool(cursor.rowcount)


class ShardJobWorker:
    """Исполнитель джобов ноды: claim → handler(kind) → complete.

    Args:
        host: имя этой ноды (как в ``aios shards add``).
        jobs: очередь (по умолчанию из env).
        handlers: {kind: callable(profile_key, payload) -> dict}.
            None → :func:`default_handlers` (shell-out в aios_cli).
    """

    def __init__(
        self,
        host: str,
        jobs: Optional[ShardJobs] = None,
        handlers: Optional[Dict[str, Callable]] = None,
    ) -> None:
        self.host = host
        self.jobs = jobs or ShardJobs()
        self.handlers = handlers if handlers is not None else default_handlers()

    def work_once(self) -> Optional[Dict]:
        """Исполнить одну джобу ноды; None — очередь пуста.

        Handler изолирован: исключение → джоба ``failed`` с текстом
        ошибки (соседние джобы не страдают).
        """
        job = self.jobs.claim_next(self.host)
        if job is None:
            return None
        handler = self.handlers.get(job["kind"])
        if handler is None:
            self.jobs.complete(
                job["id"], ok=False,
                result={"error": f"unknown job kind: {job['kind']}"},
            )
            return {"job": job["id"], "kind": job["kind"], "status": "failed",
                    "error": "unknown job kind"}
        try:
            result = handler(job["profile_key"], job["payload"]) or {}
            self.jobs.complete(job["id"], ok=True, result=result)
            return {"job": job["id"], "kind": job["kind"],
                    "status": "done", "result": result}
        except Exception as exc:  # noqa: BLE001 — изолируем джобу
            self.jobs.complete(
                job["id"], ok=False, result={"error": str(exc)[:300]},
            )
            return {"job": job["id"], "kind": job["kind"],
                    "status": "failed", "error": str(exc)[:300]}


def default_handlers(cli_path: Optional[str] = None) -> Dict[str, Callable]:
    """Встроенные виды джоб: shell-out в aios_cli (guarded сохранён).

    ``autopilot`` → ``instagram autopilot --login`` для профиля
    ``instagram:<name>``; результат — код возврата и хвост stdout.
    """
    root = Path(cli_path or Path(__file__).resolve().parent.parent.parent)
    cli = str(root / "aios_cli.py")

    def autopilot(profile_key: str, payload: Dict) -> Dict:
        platform, _, name = profile_key.partition(":")
        if platform != "instagram":
            raise ValueError(
                f"autopilot job поддерживает instagram-профили, не {platform!r}"
            )
        db = str(root / "data" / f"instagram-{name}.sqlite")
        cmd = [
            "python3", cli, "instagram", "autopilot", "--login",
            "--db", db,
        ]
        args = payload.get("args") or []
        proc = subprocess.run(
            cmd + [str(arg) for arg in args],
            capture_output=True, text=True, timeout=900,
        )
        return {
            "code": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "cmd": " ".join(cmd + [str(a) for a in args]),
        }

    return {"autopilot": autopilot}
