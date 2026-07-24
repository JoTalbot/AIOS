"""Tests for the H1 batch: job-lease TTL, builtin shard jobs,
own-promote DRY-RUN, and human-like pacing.
"""

import json
import random
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path

import pytest

from aios_core.platforms import ShardJobs, ShardJobWorker, ShardRouter, shardexec
from aios_core.platforms.pacing import Pacer, pacer_from_limits
from aios_core.platforms.promote import promotion_plan

# ---------------------------------------------------------------------------
# Job-lease TTL + queue stats
# ---------------------------------------------------------------------------


def _seed_db(tmp_path):
    db = str(tmp_path / "shards.sqlite")
    router = ShardRouter(db)
    router.add_host("worker-1", "http://10.0.0.1:8001")
    router.route_for("instagram:main")  # sticky-маршрут на worker-1
    router.close()
    return db


def _claimed_job(db, claimed_at):
    with ShardJobs(db) as jobs:
        job_id = jobs.enqueue("instagram:main", "autopilot")
        with jobs._lock, jobs._conn:
            jobs._conn.execute(
                "UPDATE shard_jobs SET status='claimed', host='worker-1',"
                " claimed_at=? WHERE id=?",
                (claimed_at, job_id),
            )
        return job_id


def test_requeue_stale_returns_old_claims(tmp_path):
    db = _seed_db(tmp_path)
    old = (datetime.now(UTC) - timedelta(seconds=900)).isoformat()
    fresh = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    stale_id = _claimed_job(db, old)
    fresh_id = _claimed_job(db, fresh)
    with ShardJobs(db) as jobs:
        moved = jobs.requeue_stale(stale_after_s=600)
        assert [j["id"] for j in moved] == [stale_id]
        statuses = {j["id"]: j["status"] for j in jobs.list()}
        assert statuses[stale_id] == "pending"
        assert statuses[fresh_id] == "claimed"
        # Зависшая снова доступна ноде:
        reclaimed = jobs.claim_next("worker-1")
        assert reclaimed["id"] == stale_id


def test_queue_stats_and_heartbeats(tmp_path):
    db = _seed_db(tmp_path)
    with ShardJobs(db) as jobs:
        jobs.enqueue("instagram:main", "autopilot")
        jobs.heartbeat("worker-1")
        stats = jobs.stats(stale_after_s=600)
        assert stats["pending"] == 1 and stats["queue_depth"] == 1
        assert stats["stale_claimed"] == 0
        assert "worker-1" in stats["heartbeats"]


def test_worker_writes_heartbeat(tmp_path):
    db = _seed_db(tmp_path)
    with ShardJobs(db) as jobs:
        worker = ShardJobWorker(host="worker-1", jobs=jobs, handlers={})
        assert worker.work_once() is None  # idle, но heartbeat записан
        assert "worker-1" in jobs.stats()["heartbeats"]


def test_cli_jobs_stats_and_requeue(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    db = _seed_db(tmp_path)
    monkeypatch.setenv("AIOS_SHARDS_DB", db)
    old = (datetime.now(UTC) - timedelta(seconds=3600)).isoformat()
    _claimed_job(db, old)
    main(["shards", "jobs", "--stats"])
    stats = json.loads(capsys.readouterr().out)
    assert stats["claimed"] == 1 and stats["stale_claimed"] == 1
    main(["shards", "requeue-stale", "--ttl", "600"])
    out = json.loads(capsys.readouterr().out)
    assert out["requeued"] == 1
    assert out["jobs"][0]["requeued_age_s"] >= 3500


# ---------------------------------------------------------------------------
# Builtin job kinds (default_handlers)
# ---------------------------------------------------------------------------


def test_default_handlers_all_kinds_shell_out(tmp_path, monkeypatch):
    ran = []

    def fake_run(cmd, **kwargs):
        ran.append(cmd)

        class _P:
            returncode = 0
            stdout = "{}"

        return _P()

    monkeypatch.setattr(shardexec.subprocess, "run", fake_run)
    handlers = shardexec.default_handlers(cli_path=str(tmp_path))
    assert set(handlers) == {"autopilot", "reels", "dm-flush", "marker-check"}

    for kind in ("reels", "dm-flush"):
        result = handlers[kind]("instagram:main", {"args": ["--max", "3"]})
        assert result["code"] == 0
        assert any(
            kind.replace("-", "-") in part or "reels" in part or "dm-flush" in part
            for part in ran[-1]
        )
        assert any("instagram-main.sqlite" in part for part in ran[-1])
        with pytest.raises(ValueError, match="instagram"):
            handlers[kind]("olx:main", {})

    result = handlers["marker-check"]("instagram:main", {})
    assert result["code"] == 0
    cmd = " ".join(ran[-1])
    assert "platforms marker-check" in cmd and "--platform instagram" in cmd
    assert "marker-instagram.xml" in cmd


# ---------------------------------------------------------------------------
# Human-like pacing
# ---------------------------------------------------------------------------


def test_pacer_jitter_and_stats():
    rng = random.Random(7)
    slept = []
    pacer = Pacer(
        actions_per_hour=0, jitter_s=(0.1, 0.2), rng=rng, sleeper=slept.append, now=lambda: 1000.0
    )
    assert pacer.before_action() is True
    assert pacer.before_action() is True
    assert len(slept) == 2
    assert all(0.1 <= s <= 0.2 for s in slept)
    assert pacer.stats()["actions"] == 2


def test_pacer_hour_quota_honest_stop():
    pacer = Pacer(actions_per_hour=2, jitter_s=None, now=lambda: 500.0)
    assert pacer.before_action() is True
    assert pacer.before_action() is True
    assert pacer.before_action() is False  # квота исчерпана — стоп


def test_pacer_session_limit_and_window_rotation():
    clock = [0.0]
    pacer = Pacer(actions_per_hour=1, session_max_s=None, jitter_s=None, now=lambda: clock[0])
    assert pacer.before_action() is True
    assert pacer.before_action() is False
    clock[0] += 3601.0  # новое окно — снова можно
    assert pacer.before_action() is True

    pacer2 = Pacer(session_max_s=10.0, jitter_s=None, now=lambda: clock[0])
    clock[0] += 11.0
    assert pacer2.before_action() is False  # сессия дольше лимита


def test_pacer_from_pool_limits():
    limits = {
        "pacing:instagram:main:actions_per_hour": 3,
        "pacing:instagram:main:session_max_s": 120,
    }
    pacer = pacer_from_limits(
        "instagram:main",
        lambda key, default=None: limits.get(key, default),
        jitter_s=None,
        now=lambda: 1.0,
    )
    assert pacer.actions_per_hour == 3
    assert pacer.session_max_s == 120.0
    pacer2 = pacer_from_limits(
        "ghost",
        lambda key, default=None: default,
        jitter_s=None,
    )
    assert pacer2.actions_per_hour is None  # без ключей — без лимита


def test_collectors_stop_on_pacing(tmp_path):
    from aios_core.platforms import PlatformDescriptor
    from aios_core.platforms.reelscout import ReelsCollector
    from aios_core.platforms.videocards import HintVideoParser

    class _ADB:
        package = "com.instagram.android"

        @property
        def adb(self):
            return "adb"

        def run(self, command):
            return {"code": 0, "stdout": "", "stderr": ""}

        def dump_ui(self, filename="screen.xml"):
            Path(filename).write_text(
                "<hierarchy><node text='' "
                "resource-id='com.instagram.android:id/reel_card'>"
                "<node text='V' resource-id=''/>"
                "<node text='0:15' resource-id=''/>"
                "</node></hierarchy>",
                encoding="utf-8",
            )
            return {"code": 0, "stdout": "", "stderr": ""}

        def swipe(self, *a, **k):
            return {"code": 0, "stdout": "", "stderr": ""}

        def tap(self, x, y):
            return {"code": 0, "stdout": "", "stderr": ""}

        def input_text(self, text):
            return {"code": 0, "stdout": "", "stderr": ""}

    # квота 1 действие: лента бесконечная, но цикл обрублен честно:
    pacer = Pacer(actions_per_hour=1, jitter_s=None, now=lambda: 0.0)
    collector = ReelsCollector(
        PlatformDescriptor(
            name="instagram", android_package="com.instagram.android", agent_module="x"
        ),
        adb=_ADB(),
        parser=HintVideoParser(["reel_card"]),
        pacer=pacer,
    )
    cards = collector.collect(max_cards=100, stop_after_empty=99)
    # Дампы идентичны → карточка одна; главное — свайп разрешён лишь 1 раз:
    assert len(cards) == 1
    assert pacer.stats()["window_actions"] == 1


def test_instagram_collector_pacer_passthrough():
    from aios_core.modules.instagram import InstagramCollector

    pacer = Pacer(actions_per_hour=5, jitter_s=None, now=lambda: 0.0)
    collector = InstagramCollector(parser="x", pacer=pacer)
    engine = collector._collector()
    assert engine.pacer is pacer


# ---------------------------------------------------------------------------
# Own-promote DRY-RUN
# ---------------------------------------------------------------------------


def test_promotion_plan_even_budget_and_dry_run():
    stagnant = [
        {
            "fingerprint": f"fp{i}",
            "title": f"Пост {i}",
            "views_per_day": 0.2 * i,
            "age_days": 5.0 + i,
        }
        for i in range(1, 8)
    ]
    plan = promotion_plan(stagnant, daily_budget=150.0, max_items=3)
    assert plan["dry_run"] is True
    assert len(plan["candidates"]) == 3
    assert all(c["action"] == "boost" for c in plan["candidates"])
    assert plan["candidates"][0]["est_daily_cost"] == 50.0
    assert plan["budget"] == 150.0 and plan["currency"] == "UAH"
    assert "DRY-RUN" in plan["note"]

    no_budget = promotion_plan(stagnant[:1], daily_budget=None)
    assert no_budget["candidates"][0]["est_daily_cost"] is None


def test_cli_autopilot_promote_step(tmp_path, capsys, monkeypatch):
    import yaml

    from aios_cli import main
    from aios_core.modules.instagram import InstagramStorage
    from aios_core.modules.olx.own_ads import OwnAd

    (tmp_path / "instagram.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "instagram",
                "android_package": "com.instagram.android",
                "extras": {"parser_hints": {}},
            }
        ),
        encoding="utf-8",
    )

    # Зрелый пост с почти нулевыми просмотрами → stagnant:
    db = tmp_path / "ig.sqlite"
    storage = InstagramStorage(str(db))
    old = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    storage.upsert_own_ad(
        OwnAd(
            title="Старий пост",
            views=2,
            favorites=0,
            messages=0,
        ),
        seen_at=old,
    )
    storage.close()

    from aios_core.modules.olx import adb as adb_mod

    feed = "<hierarchy><node text='' resource-id=''/></hierarchy>"
    monkeypatch.setattr(
        adb_mod,
        "ADBController",
        lambda *a, **k: _CliADB([feed, feed]),
    )
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    from aios_core.platforms import ProfileStore

    ProfileStore.reset_default()

    from aios_core.platforms import descriptor as descriptor_mod
    from aios_core.platforms import load_catalog_file

    loaded = load_catalog_file("platforms/instagram.yaml")
    try:
        main(
            [
                "instagram",
                "autopilot",
                "--db",
                str(db),
                "--max",
                "1",
                "--reels-max",
                "1",
                "--directory",
                str(tmp_path),
                "--promote",
                "--promote-budget",
                "100",
            ]
        )
    finally:
        descriptor_mod._PLATFORMS.pop(loaded[0].name, None)
    out = json.loads(capsys.readouterr().out)
    promote = out["steps"]["promote"]
    assert promote["dry_run"] is True
    assert promote["candidates"][0]["title"] == "Старий пост"
    assert promote["candidates"][0]["est_daily_cost"] == 100.0
    assert promote["notified"] is False  # без --webhook


class _CliADB:
    package = "com.instagram.android"

    def __init__(self, dumps=()):
        self.dumps = list(dumps)
        self.calls = []

    @property
    def adb(self):
        return "adb"

    def run(self, command):
        self.calls.append(command)
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename="screen.xml"):
        if not self.dumps:
            return {"code": 1, "stdout": "", "stderr": "no dumps"}
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}

    def tap(self, x, y):
        return {"code": 0, "stdout": "", "stderr": ""}

    def swipe(self, *a, **k):
        return {"code": 0, "stdout": "", "stderr": ""}

    def input_text(self, text):
        return {"code": 0, "stdout": "", "stderr": ""}
