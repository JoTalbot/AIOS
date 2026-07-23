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
CREATE TABLE IF NOT EXISTS shard_heartbeats (
    host TEXT PRIMARY KEY,
    seen_at TEXT NOT NULL
);
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
        """Clean up resources."""
        self._conn.close()

    # -- очередь ------------------------------------------------------

    def enqueue(self, profile_key: str, kind: str, payload: Optional[Dict] = None) -> int:
        """Повесить джобу на профиль; вернуть id."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO shard_jobs (profile_key, kind, payload, enqueued_at)"
                " VALUES (?, ?, ?, ?)",
                (
                    profile_key,
                    kind,
                    json.dumps(payload or {}, ensure_ascii=False),
                    _now(),
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
                pass  # Non-JSON result — keep as-is
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
            job for job in self.list(status="pending") if self._host_for(job["profile_key"]) == host
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

    def complete(self, job_id: int, ok: bool = True, result: Optional[Dict] = None) -> bool:
        """Зафиксировать результат джобы (done/failed)."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE shard_jobs SET status = ?, finished_at = ?, result = ? " "WHERE id = ?",
                (
                    "done" if ok else "failed",
                    _now(),
                    json.dumps(result or {}, ensure_ascii=False),
                    job_id,
                ),
            )
            return bool(cursor.rowcount)

    # -- lease TTL / метрики ------------------------------------------

    def heartbeat(self, host: str) -> None:
        """Исполнитель жив: обновляет отметку времени ноды."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO shard_heartbeats (host, seen_at)" " VALUES (?, ?)",
                (host, _now()),
            )

    def requeue_stale(self, stale_after_s: float = 600.0, now: Optional[str] = None) -> List[Dict]:
        """Вернуть в pending claimed-джобы, зависшие дольше TTL.

        Джоба считается зависшей, если с момента claim прошло больше
        ``stale_after_s`` секунд (нода умерла/повисла). Host снимается —
        следующий claim переоценит маршрут.
        """
        from datetime import datetime as _dt

        now_dt = _dt.fromisoformat(now) if now else _dt.now(timezone.utc)
        moved: List[Dict] = []
        with self._lock, self._conn:
            for job in self.list(status="claimed"):
                claimed = job.get("claimed_at")
                if not claimed:
                    continue
                age = (now_dt - _dt.fromisoformat(claimed)).total_seconds()
                if age < stale_after_s:
                    continue
                self._conn.execute(
                    "UPDATE shard_jobs SET status = 'pending', host = NULL, "
                    "claimed_at = NULL WHERE id = ?",
                    (job["id"],),
                )
                job["status"] = "pending"
                job["host"] = None
                job["requeued_age_s"] = round(age, 3)
                moved.append(job)
        return moved

    def stats(self, stale_after_s: float = 600.0, now: Optional[str] = None) -> Dict:
        """Глубина очереди и счётчики по статусам (+зависшие claim'ы)."""
        from datetime import datetime as _dt

        now_dt = _dt.fromisoformat(now) if now else _dt.now(timezone.utc)
        counts: Dict[str, int] = {}
        with self._lock:
            for row in self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM shard_jobs GROUP BY status"
            ).fetchall():
                counts[row["status"]] = int(row["n"])
            heartbeats = {
                row["host"]: row["seen_at"]
                for row in self._conn.execute(
                    "SELECT host, seen_at FROM shard_heartbeats"
                ).fetchall()
            }

        def _age(ts: str) -> float:
            return (now_dt - _dt.fromisoformat(ts)).total_seconds()

        stale = sum(
            1
            for job in self.list(status="claimed")
            if job.get("claimed_at") and _age(job["claimed_at"]) >= stale_after_s
        )
        return {
            "pending": counts.get("pending", 0),
            "claimed": counts.get("claimed", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
            "queue_depth": counts.get("pending", 0) + counts.get("claimed", 0),
            "stale_claimed": stale,
            "heartbeats": heartbeats,
        }


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
        self.jobs.heartbeat(self.host)
        job = self.jobs.claim_next(self.host)
        if job is None:
            return None
        handler = self.handlers.get(job["kind"])
        if handler is None:
            self.jobs.complete(
                job["id"],
                ok=False,
                result={"error": f"unknown job kind: {job['kind']}"},
            )
            return {
                "job": job["id"],
                "kind": job["kind"],
                "status": "failed",
                "error": "unknown job kind",
            }
        try:
            result = handler(job["profile_key"], job["payload"]) or {}
            self.jobs.complete(job["id"], ok=True, result=result)
            return {
                "job": job["id"],
                "kind": job["kind"],
                "status": "done",
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001 — изолируем джобу
            self.jobs.complete(
                job["id"],
                ok=False,
                result={"error": str(exc)[:300]},
            )
            return {
                "job": job["id"],
                "kind": job["kind"],
                "status": "failed",
                "error": str(exc)[:300],
            }


def default_handlers(cli_path: Optional[str] = None) -> Dict[str, Callable]:
    """Встроенные виды джоб: shell-out в aios_cli (guarded сохранён).

    ``autopilot`` → ``instagram autopilot --login`` для профиля
    ``instagram:<name>``; результат — код возврата и хвост stdout.
    """
    root = Path(cli_path or Path(__file__).resolve().parent.parent.parent)
    cli = str(root / "aios_cli.py")

    def _run_cli(cmd: List[str], extra: List) -> Dict:
        args = [str(arg) for arg in (extra or [])]
        proc = subprocess.run(
            cmd + args,
            capture_output=True,
            text=True,
            timeout=900,
        )
        return {
            "code": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "cmd": " ".join(cmd + args),
        }

    def _profile_db(platform: str, name: str) -> str:
        return str(root / "data" / f"{platform}-{name}.sqlite")

    def autopilot(profile_key: str, payload: Dict) -> Dict:
        """Execute autopilot."""
        platform, _, name = profile_key.partition(":")
        if platform != "instagram":
            raise ValueError(f"autopilot job поддерживает instagram-профили, не {platform!r}")
        return _run_cli(
            [
                "python3",
                cli,
                "instagram",
                "autopilot",
                "--login",
                "--db",
                _profile_db(platform, name),
            ],
            payload.get("args"),
        )

    def reels(profile_key: str, payload: Dict) -> Dict:
        """Execute reels."""
        platform, _, name = profile_key.partition(":")
        if platform != "instagram":
            raise ValueError(f"reels job поддерживает instagram-профили, не {platform!r}")
        return _run_cli(
            [
                "python3",
                cli,
                "instagram",
                "reels",
                "--open-tab",
                "--db",
                _profile_db(platform, name),
            ],
            payload.get("args"),
        )

    def dm_flush(profile_key: str, payload: Dict) -> Dict:
        """Execute dm flush."""
        platform, _, name = profile_key.partition(":")
        if platform != "instagram":
            raise ValueError(f"dm-flush job поддерживает instagram-профили, не {platform!r}")
        return _run_cli(
            [
                "python3",
                cli,
                "instagram",
                "dm-flush",
                "--db",
                _profile_db(platform, name),
            ],
            payload.get("args"),
        )

    def marker_check(profile_key: str, payload: Dict) -> Dict:
        """Execute marker check."""
        platform, _, _name = profile_key.partition(":")
        dump = str(root / "data" / f"marker-{platform}.xml")
        return _run_cli(
            [
                "python3",
                cli,
                "platforms",
                "marker-check",
                "--platform",
                platform,
                "--dump",
                dump,
            ],
            payload.get("args"),
        )

    return {
        "autopilot": autopilot,
        "reels": reels,
        "dm-flush": dm_flush,
        "marker-check": marker_check,
    }
