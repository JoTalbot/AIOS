"""Тесты ядра Phone Brain: очередь, backoff супервизора, гейты исполнителя."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_core.phone_brain.common import iso, utc_now
from aios_core.phone_brain.device import DeviceSupervisor
from aios_core.phone_brain.events import EventLog
from aios_core.phone_brain.handlers import Executor, Handler, JobContext
from aios_core.phone_brain.queue_store import JobStore


@pytest.fixture()
def store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path / "queue.db", retry_base_seconds=10, retry_cap_seconds=120,
                    lease_seconds=60, default_max_attempts=3)


# ------------------------------------------------------------------ JobStore

def test_enqueue_claim_complete(store: JobStore) -> None:
    job = store.enqueue("kind.a", {"x": 1})
    assert job["id"] >= 1 and job["status"] == "queued"
    claimed = store.claim()
    assert claimed and claimed["id"] == job["id"] and claimed["status"] == "running"
    assert claimed["attempts"] == 1 and claimed["payload"] == {"x": 1}
    assert store.claim() is None  # пусто
    assert store.complete(claimed["id"], claimed["lease_token"], {"r": 2})
    done = store.get(claimed["id"])
    assert done["status"] == "done" and done["result"] == {"r": 2}


def test_priority_order(store: JobStore) -> None:
    low = store.enqueue("kind.low", priority=10)
    high = store.enqueue("kind.high", priority=90)
    assert store.claim()["id"] == high["id"]
    assert store.claim()["id"] == low["id"]


def test_retry_backoff_then_terminal(store: JobStore) -> None:
    job = store.enqueue("kind.fail", max_attempts=3)
    # попытка 1 → повтор через ~10с
    claimed = store.claim()
    outcome = store.fail(claimed["id"], claimed["lease_token"], "boom")
    assert outcome["retried"] and outcome["delay_seconds"] == 10
    queued = store.get(job["id"])
    assert queued["status"] == "queued" and queued["run_after"] > iso()
    assert store.claim() is None  # run_after в будущем
    # насильно делаем задачу доступной и добиваем попытки
    with store._db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE jobs SET run_after='' WHERE id=?", (job["id"],))
    claimed2 = store.claim()
    assert claimed2["attempts"] == 2
    outcome2 = store.fail(claimed2["id"], claimed2["lease_token"], "boom2")
    assert outcome2["delay_seconds"] == 20  # экспонента 10*2
    with store._db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE jobs SET run_after='' WHERE id=?", (job["id"],))
    claimed3 = store.claim()
    outcome3 = store.fail(claimed3["id"], claimed3["lease_token"], "boom3")
    assert outcome3["status"] == "failed" and not outcome3["retried"]
    assert store.get(job["id"])["status"] == "failed"


def test_fail_without_retry(store: JobStore) -> None:
    job = store.enqueue("kind.fatal")
    claimed = store.claim()
    outcome = store.fail(claimed["id"], claimed["lease_token"], "fatal", retry=False)
    assert outcome["status"] == "failed" and store.get(job["id"])["status"] == "failed"


def test_defer_does_not_burn_attempts_and_has_limit(store: JobStore) -> None:
    store.defer_limit = 2

    def make_due(job_id: int) -> None:
        with store._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE jobs SET run_after='' WHERE id=?", (job_id,))

    job = store.enqueue("kind.offline")
    claimed = store.claim()
    outcome = store.defer(claimed["id"], claimed["lease_token"], reason="device_offline")
    assert outcome["deferred"]
    assert store.get(job["id"])["attempts"] == 0  # попытка возвращена
    make_due(job["id"])
    claimed2 = store.claim()
    assert claimed2["attempts"] == 1
    outcome2 = store.defer(claimed2["id"], claimed2["lease_token"], reason="device_offline")
    assert outcome2["deferrals"] == 2
    make_due(job["id"])
    claimed3 = store.claim()
    outcome3 = store.defer(claimed3["id"], claimed3["lease_token"], reason="device_offline")
    assert outcome3["status"] == "failed"
    failed = store.get(job["id"])
    assert failed["status"] == "failed" and "device_offline" in (failed["error"] or "")


def test_dedup_key(store: JobStore) -> None:
    first = store.enqueue("kind.d", dedup_key="k-1")
    second = store.enqueue("kind.d", dedup_key="k-1")
    assert second["duplicate"] and second["id"] == first["id"]
    store.claim()
    third = store.enqueue("kind.d", dedup_key="k-1")
    assert third["duplicate"]  # running тоже считается активной


def test_cancel_and_purge(store: JobStore) -> None:
    job = store.enqueue("kind.c")
    assert store.cancel(job["id"])["status"] == "ok"
    assert store.cancel(job["id"])["status"] == "error"  # уже терминальный
    old = utc_now() - timedelta(days=30)
    with store._db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE jobs SET finished_at=? WHERE id=?", (iso(old), job["id"]))
    assert store.purge(retention_days=7) == 1
    assert store.get(job["id"]) is None


def test_requeue_expired(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "q.db", lease_seconds=-1)  # lease сразу «в прошлом»
    job = store.enqueue("kind.exp")
    claimed = store.claim()
    assert claimed
    assert store.requeue_expired() == 1
    again = store.claim()
    assert again["id"] == job["id"] and again["attempts"] == 2


# ------------------------------------------------------------ DeviceSupervisor

class FakeGateway:
    """Программируемый двойник AndroidGateway (без ADB)."""

    def __init__(self, statuses: list[dict]):
        self._statuses = list(statuses)
        self.connect_calls = 0

    def status(self) -> dict:
        if len(self._statuses) > 1:
            return self._statuses.pop(0)
        return self._statuses[0]

    def connect(self) -> dict:
        self.connect_calls += 1
        return {"status": "ok", "message": "connected to 10.0.0.1:5555"}


class FakeClock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, seconds: float) -> None:
        self.moment += timedelta(seconds=seconds)


OFFLINE = {"status": "offline", "connected": False, "serial": "s1"}
ONLINE = {"status": "ok", "connected": True, "serial": "s1",
          "companion": {"status": "ok", "connected": True}, "checked_at": ""}


def test_supervisor_backoff_and_recovery(tmp_path: Path) -> None:
    clock = FakeClock()
    gateway = FakeGateway([dict(OFFLINE) for _ in range(5)] + [dict(ONLINE) for _ in range(5)])
    events = EventLog(tmp_path / "events.jsonl")
    supervisor = DeviceSupervisor(tmp_path, gateway=gateway, min_interval=30, max_interval=120,
                                  escalate_after_seconds=300, events=events, now_fn=clock)

    health1 = supervisor.poll()  # status→OFF, probe→OFF
    assert health1["status"] == "offline"
    assert gateway.connect_calls == 1
    assert health1["brain"]["backoff_seconds"] == 30

    # повтор до next_attempt — новых попыток connect нет
    clock.advance(10)
    supervisor.poll()
    assert gateway.connect_calls == 1

    # после backoff-окна — вторая попытка, интервал вырос
    clock.advance(25)
    state2 = supervisor.poll()
    assert gateway.connect_calls == 2
    assert state2["brain"]["backoff_seconds"] == 60


def test_supervisor_recovery_resets_backoff(tmp_path: Path) -> None:
    clock = FakeClock()
    # poll1: status=OFF, probe=OFF; poll2: status=OFF; advance; poll3: status=ON
    gateway = FakeGateway([dict(OFFLINE) for _ in range(3)] + [dict(ONLINE) for _ in range(10)])
    supervisor = DeviceSupervisor(tmp_path, gateway=gateway, min_interval=30, now_fn=clock)
    supervisor.poll()
    assert supervisor.poll()["status"] == "offline"
    clock.advance(31)
    health = supervisor.poll()
    assert health["status"] == "ok"
    state = supervisor._state()
    assert state["fail_streak"] == 0 and not state["offline_since"]


def test_supervisor_escalates_once(tmp_path: Path) -> None:
    clock = FakeClock()
    gateway = FakeGateway([dict(OFFLINE) for _ in range(30)])
    events = EventLog(tmp_path / "events.jsonl")
    supervisor = DeviceSupervisor(tmp_path, gateway=gateway, min_interval=60, max_interval=60,
                                  escalate_after_seconds=120, events=events, now_fn=clock)
    supervisor.poll()
    clock.advance(60)
    supervisor.poll()
    clock.advance(60)
    supervisor.poll()
    escalations = [e for e in events.recent() if e["type"] == "device_offline_escalated"]
    assert len(escalations) == 1  # эскалация однократная, не спам


# ------------------------------------------------------------------ Executor

def _ctx(online: bool = True, companion: bool = True) -> JobContext:
    supervisor = SimpleNamespace(is_online=lambda: online, companion_ready=lambda: companion)
    return JobContext(root=Path("/tmp"), gateway=None, supervisor=supervisor, events=None)


def _job(kind: str, payload: dict | None = None) -> dict:
    return {"id": 1, "kind": kind, "payload": payload or {}, "lease_token": "t"}


def test_executor_unknown_kind() -> None:
    verdict, payload = Executor(_ctx(), handlers=[]).execute(_job("nope"))
    assert verdict == "fail" and payload["retry"] is False


def test_executor_confirm_gate() -> None:
    executor = Executor(_ctx(), handlers=[
        Handler("danger", lambda p, c: {"status": "ok"}, confirm_action="do_danger")])
    verdict, payload = executor.execute(_job("danger"))
    assert verdict == "need_confirm" and payload["action"] == "do_danger"
    verdict2, _ = executor.execute(_job("danger", {"confirm": True}))
    assert verdict2 == "done"


def test_executor_offline_defers() -> None:
    executor = Executor(_ctx(online=False), handlers=[
        Handler("dev", lambda p, c: {"status": "ok"}, needs_device=True)])
    verdict, payload = executor.execute(_job("dev"))
    assert verdict == "defer" and payload["reason"] == "device_offline"


def test_executor_companion_defers() -> None:
    executor = Executor(_ctx(online=True, companion=False), handlers=[
        Handler("ui", lambda p, c: {"status": "ok"}, needs_companion=True)])
    verdict, payload = executor.execute(_job("ui"))
    assert verdict == "defer" and payload["reason"] == "companion_offline"


def test_executor_handler_error_and_timeout() -> None:
    def boom(payload: dict, ctx: JobContext) -> dict:
        raise RuntimeError("сбой")

    def slow(payload: dict, ctx: JobContext) -> dict:
        time.sleep(2)
        return {"status": "ok"}

    executor = Executor(_ctx(), handlers=[
        Handler("boom", boom), Handler("slow", slow, timeout=1),
        Handler("err", lambda p, c: {"status": "error", "error": "ло́гика"}),
        Handler("off", lambda p, c: {"status": "offline"})])
    verdict, payload = executor.execute(_job("boom"))
    assert verdict == "fail" and "сбой" in payload["error"]
    verdict, payload = executor.execute(_job("slow"))
    assert verdict == "fail" and "Таймаут" in payload["error"]
    verdict, payload = executor.execute(_job("err"))
    assert verdict == "fail" and payload["error"] == "ло́гика"
    verdict, _ = executor.execute(_job("off"))
    assert verdict == "defer"


def test_executor_precheck_need_confirm() -> None:
    def check(payload: dict) -> dict | None:
        return {"status": "need_confirm", "action": "text"} if payload.get("risky") else None

    executor = Executor(_ctx(), handlers=[
        Handler("snap", lambda p, c: {"status": "ok"}, needs_device=False, precheck=check)])
    verdict, _ = executor.execute(_job("snap", {"risky": True}))
    assert verdict == "need_confirm"
    verdict, _ = executor.execute(_job("snap"))
    assert verdict == "done"
