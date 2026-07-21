"""Tests for navigation autocalibration (reels_tab), the own-posts
autopilot step, and shard-execute pull-model jobs.
"""

import json
from pathlib import Path

import pytest
import yaml

from aios_core.modules.instagram import InstagramStorage
from aios_core.platforms import (
    DetailCalibrationAdvisor,
    ShardJobs,
    ShardJobWorker,
    ShardRouter,
    merge_hints,
    reels_driver_for,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HOME_NAV_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/tab_bar">
    <node content-desc="Home" resource-id="com.instagram.android:id/home_tab"
          bounds="[0,2300][270,2400]"/>
    <node content-desc="Search" resource-id="com.instagram.android:id/search_tab"
          bounds="[270,2300][540,2400]"/>
    <node content-desc="Reels" resource-id="com.instagram.android:id/reels_tab"
          bounds="[540,2300][810,2400]"/>
    <node content-desc="Profile" resource-id="com.instagram.android:id/profile_tab"
          bounds="[810,2300][1080,2400]"/>
  </node>
</hierarchy>
"""

HOME_NO_REELS_XML = """<hierarchy>
  <node text="" resource-id="com.demo:id/bottom_nav">
    <node content-desc="Home" resource-id="com.demo:id/home_tab"
          bounds="[0,2300][270,2400]"/>
    <node content-desc="Profile" resource-id="com.demo:id/profile_tab"
          bounds="[270,2300][540,2400]"/>
  </node>
</hierarchy>"""

HOME_NO_BAR_XML = '<hierarchy><node text="feed" resource-id="x"/></hierarchy>'

GRID_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/row_profile_grid_item">
    <node text="Наші нові кросівки" resource-id=""/>
    <node text="1 234 перегляди" resource-id=""/>
    <node text="56 вподобань" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/row_profile_grid_item">
    <node text="Сумка в наявності" resource-id=""/>
    <node text="88 likes" resource-id=""/>
  </node>
</hierarchy>
"""

GRID_XML_SHRUNK = """<hierarchy>
  <node text="" resource-id="com.instagram.android:id/row_profile_grid_item">
    <node text="Наші нові кросівки" resource-id=""/>
    <node text="1 300 переглядів" resource-id=""/>
    <node text="60 вподобань" resource-id=""/>
  </node>
</hierarchy>
"""

FEED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Кросівки Nike Air" resource-id=""/>
    <node text="3 200 грн" resource-id=""/>
  </node>
</hierarchy>
"""

EMPTY_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"


class _ADB:
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
            return {"code": 1, "stdout": "", "stderr": "no dumps left"}
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}

    def tap(self, x, y):
        self.calls.append(("tap", x, y))
        return {"code": 0, "stdout": "", "stderr": ""}

    def swipe(self, *args, **kwargs):
        self.calls.append(("swipe", args))
        return {"code": 0, "stdout": "", "stderr": ""}

    def input_text(self, text):
        self.calls.append(("input_text", text))
        return {"code": 0, "stdout": "", "stderr": ""}


class _Notifier:
    def __init__(self):
        self.events = []

    def send(self, event, data):
        self.events.append((event, data))
        return True


# ---------------------------------------------------------------------------
# Navigation autocalibration
# ---------------------------------------------------------------------------

def test_analyze_navigation_finds_reels_tab():
    hints = DetailCalibrationAdvisor().analyze_navigation(HOME_NAV_XML)
    tab = hints["reels_tab"]
    assert tab["rid_markers"] == [
        {"resource_id": "com.instagram.android:id/reels_tab"}]
    assert tab["text_markers"] == ["Reels"]
    assert tab["bounds"] == "[540,2300][810,2400]"
    assert hints["tab_bar_markers"] == [
        {"resource_id": "com.instagram.android:id/tab_bar"}]
    assert len(hints["tabs"]) == 4
    assert hints["hint"] == "видео-вкладка найдена"


def test_analyze_navigation_no_reels_honest():
    hints = DetailCalibrationAdvisor().analyze_navigation(HOME_NO_REELS_XML)
    assert hints["reels_tab"] == {}
    assert hints["tab_bar_markers"]  # бар есть — честный диагноз вкладки
    assert "не распознана" in hints["hint"]
    hints2 = DetailCalibrationAdvisor().analyze_navigation(HOME_NO_BAR_XML)
    assert hints2["reels_tab"] == {}
    assert hints2["tab_bar_markers"] == []
    assert "tab-bar не найден" in hints2["hint"]


def test_merge_hints_navigation_key():
    nav = DetailCalibrationAdvisor().analyze_navigation(HOME_NAV_XML)
    merged = merge_hints({"card_markers": []}, navigation=nav)
    assert merged["navigation"]["reels_tab"]["rid_markers"]
    assert "navigation" not in merge_hints({"card_markers": []})  # обр. совм.


def test_navigation_hints_roundtrip_into_driver(tmp_path):
    nav = DetailCalibrationAdvisor().analyze_navigation(HOME_NAV_XML)
    (tmp_path / "instagram.yaml").write_text(yaml.safe_dump({
        "name": "instagram",
        "android_package": "com.instagram.android",
        "extras": {"parser_hints": {"navigation": nav}},
    }), encoding="utf-8")
    driver = reels_driver_for("instagram", adb=_ADB([]), directory=str(tmp_path))
    assert driver.rid_markers == ("reels_tab",)
    assert "reels" in driver.text_markers
    # И тап работает по автокалиброванным маркерам:
    adb = _ADB([HOME_NAV_XML])
    driver = reels_driver_for(
        "instagram", adb=adb, directory=str(tmp_path),
        open_wait_s=0, sleeper=lambda s: None,
    )
    assert driver.drive() is True
    assert ("tap", 675, 2350) in adb.calls


def test_cli_calibrate_navigation_write(tmp_path, capsys):
    from aios_cli import main
    from aios_core.platforms import scaffold_platform

    monkey_cwd = tmp_path
    scaffold_platform(
        "navdemo", "com.nav.demo", project_root=str(monkey_cwd),
    )
    home = tmp_path / "home.xml"
    home.write_text(HOME_NAV_XML, encoding="utf-8")
    feed = tmp_path / "feed.xml"
    feed.write_text("<hierarchy/>", encoding="utf-8")
    import os
    old = os.getcwd()
    os.chdir(monkey_cwd)
    try:
        main(["platforms", "calibrate", "--platform", "navdemo",
              "--dump", str(feed), "--navigation", str(home), "--write"])
    finally:
        os.chdir(old)
    out = json.loads(capsys.readouterr().out)
    assert out["written"].endswith("navdemo.yaml")
    doc = yaml.safe_load(
        (monkey_cwd / "platforms" / "navdemo.yaml").read_text(encoding="utf-8"))
    nav = doc["extras"]["parser_hints"]["navigation"]
    assert nav["reels_tab"]["rid_markers"][0]["resource_id"].endswith(
        "reels_tab")


# ---------------------------------------------------------------------------
# Own-posts → autopilot
# ---------------------------------------------------------------------------

CHAT_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node class="android.widget.EditText"
        resource-id="com.instagram.android:id/row_thread_composer_edittext"
        text="" bounds="[0,2200][900,2300]"/>
  <node content-desc="Send"
        resource-id="com.instagram.android:id/row_thread_composer_button_send"
        text="" bounds="[900,2200][1080,2300]"/>
</hierarchy>
"""


def _patch_adb(monkeypatch, fake):
    from aios_core.modules.olx import adb as adb_mod
    monkeypatch.setattr(
        adb_mod, "ADBController", lambda *args, **kwargs: fake,
    )


def _patch_notifier(monkeypatch, recorder):
    from aios_core.modules.olx import notifier as notifier_mod

    class _FakeWebhook:
        def __init__(self, url=None, **kwargs):
            self.url = url

        def send(self, event, data):
            recorder.events.append((self.url, event, data))
            return True

    monkeypatch.setattr(notifier_mod, "WebhookNotifier", _FakeWebhook)


def _write_yaml(directory, hints):
    path = Path(directory) / "instagram.yaml"
    path.write_text(yaml.safe_dump({
        "name": "instagram",
        "android_package": "com.instagram.android",
        "extras": {"parser_hints": hints},
    }, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def instagram_registered():
    from aios_core.platforms import load_catalog_file
    from aios_core.platforms import descriptor as descriptor_mod
    loaded = load_catalog_file("platforms/instagram.yaml")
    yield loaded[0]
    descriptor_mod._PLATFORMS.pop(loaded[0].name, None)


def test_cli_autopilot_own_step_new_posts_alert(tmp_path, capsys, monkeypatch,
                                                instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {
        "card_markers": [
            {"resource_id": "com.instagram.android:id/shop_card"}],
    })
    db = tmp_path / "ig.sqlite"
    grid = tmp_path / "grid.xml"
    grid.write_text(GRID_XML, encoding="utf-8")
    recorder = _Notifier()
    fake = _ADB([FEED_XML, EMPTY_XML])
    _patch_adb(monkeypatch, fake)
    _patch_notifier(monkeypatch, recorder)
    main(["instagram", "autopilot", "--db", str(db), "--max", "1",
          "--reels-max", "1", "--directory", str(tmp_path),
          "--own", "--own-dump", str(grid),
          "--webhook", "http://hook/in"])
    out = json.loads(capsys.readouterr().out)
    own = out["steps"]["own"]
    assert own["recorded"] == 2 and own["new"] == 2
    assert own["notified"] is True
    assert any(event == "own-posts" for _, event, _ in recorder.events)
    # без --own шага нет:
    fake2 = _ADB([FEED_XML, EMPTY_XML])
    _patch_adb(monkeypatch, fake2)
    main(["instagram", "autopilot", "--db", str(db), "--max", "1",
          "--reels-max", "1", "--directory", str(tmp_path)])
    out2 = json.loads(capsys.readouterr().out)
    assert "own" not in out2["steps"]


def test_cli_autopilot_own_drift_on_shrunk_counters(tmp_path, capsys,
                                                    monkeypatch,
                                                    instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {})
    db = tmp_path / "ig.sqlite"
    grid = tmp_path / "grid.xml"
    grid.write_text(GRID_XML, encoding="utf-8")

    # Первый снапшот через команду own (та же БД):
    main(["instagram", "own", "--db", str(db), "--dump", str(grid)])
    capsys.readouterr()

    # Второй снапшот со «схлопнувшимися» счётчиками — drift-дельты:
    grid.write_text(GRID_XML_SHRUNK, encoding="utf-8")
    recorder = _Notifier()
    fake = _ADB([FEED_XML, EMPTY_XML])
    _patch_adb(monkeypatch, fake)
    _patch_notifier(monkeypatch, recorder)
    main(["instagram", "autopilot", "--db", str(db), "--max", "1",
          "--reels-max", "1", "--directory", str(tmp_path),
          "--own", "--own-dump", str(grid),
          "--webhook", "http://hook/in"])
    out = json.loads(capsys.readouterr().out)
    own = out["steps"]["own"]
    assert own["deltas"]  # счётчики изменились
    own_events = [d for _, e, d in recorder.events if e == "own-posts"]
    if own["notified"]:
        assert own_events  # алёрт на негативные дельты/новые посты
    storage = InstagramStorage(str(db))
    assert storage.own_ads()  # снапшоты персистятся
    storage.close()


def test_cli_autopilot_own_live_dump_missing_is_honest(tmp_path, capsys,
                                                       monkeypatch,
                                                       instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {})
    fake = _ADB([FEED_XML, EMPTY_XML])  # own: дампов нет → честная ошибка
    _patch_adb(monkeypatch, fake)
    main(["instagram", "autopilot", "--db", str(tmp_path / "ig.sqlite"),
          "--max", "1", "--reels-max", "1", "--directory", str(tmp_path),
          "--own"])
    out = json.loads(capsys.readouterr().out)
    assert "error" in out and "own-dump" in out["error"]


# ---------------------------------------------------------------------------
# ShardExec: pull-модель джобов
# ---------------------------------------------------------------------------

def _seed_shard_db(tmp_path):
    db = str(tmp_path / "shards.sqlite")
    router = ShardRouter(db)
    router.add_host("worker-1", "http://10.0.0.1:8001")
    router.add_host("worker-2", "http://10.0.0.2:8001")
    host_a = router.route_for("instagram:main")["host"]
    router.close()
    return db, host_a


def test_shard_jobs_route_aware_claim(tmp_path):
    db, host_a = _seed_shard_db(tmp_path)
    other = "worker-1" if host_a == "worker-2" else "worker-2"
    with ShardJobs(db) as jobs:
        job_id = jobs.enqueue("instagram:main", "autopilot",
                              payload={"args": ["--max", "5"]})
        # Чужая нода джобу не получит (sticky-маршрут):
        assert jobs.pending_for(other) == []
        assert jobs.claim_next(other) is None
        mine = jobs.claim_next(host_a)
        assert mine["id"] == job_id and mine["status"] == "claimed"
        assert mine["payload"] == {"args": ["--max", "5"]}
        assert jobs.claim_next(host_a) is None  # уже забрана
        assert jobs.complete(job_id, ok=True, result={"code": 0}) is True
        done = jobs.list(status="done")
        assert done[0]["result"] == {"code": 0}


def test_shard_jobs_complete_failed_and_listing(tmp_path):
    db, _ = _seed_shard_db(tmp_path)
    with ShardJobs(db) as jobs:
        jobs.enqueue("instagram:main", "autopilot")
        jobs.enqueue("ghost:noop", "weird")
        assert len(jobs.list()) == 2
        assert len(jobs.list(status="pending")) == 2
        bad = [j for j in jobs.list(status="pending")
               if j["profile_key"] == "ghost:noop"][0]
        jobs.complete(bad["id"], ok=False, result={"error": "boom"})
        failed = jobs.list(status="failed")
        assert failed[0]["result"]["error"] == "boom"


def test_shard_worker_executes_and_isolates_errors(tmp_path):
    db, host_a = _seed_shard_db(tmp_path)
    calls = []

    def autopilot(profile_key, payload):
        calls.append((profile_key, payload))
        return {"code": 0}

    def broken(profile_key, payload):
        raise RuntimeError("handler exploded")

    with ShardJobs(db) as jobs:
        jobs.enqueue("instagram:main", "autopilot")
        jobs.enqueue("instagram:main", "broken")
        worker = ShardJobWorker(
            host=host_a, jobs=jobs,
            handlers={"autopilot": autopilot, "broken": broken},
        )
        first = worker.work_once()
        assert first["status"] == "done" and first["result"] == {"code": 0}
        assert calls == [("instagram:main", {})]
        second = worker.work_once()
        assert second["status"] == "failed"
        assert "handler exploded" in second["error"]
        assert worker.work_once() is None
        assert len(jobs.list(status="done")) == 1
        assert len(jobs.list(status="failed")) == 1


def test_shard_worker_unknown_kind_fails_honestly(tmp_path):
    db, host_a = _seed_shard_db(tmp_path)
    with ShardJobs(db) as jobs:
        jobs.enqueue("instagram:main", "mystery")
        worker = ShardJobWorker(host=host_a, jobs=jobs, handlers={})
        result = worker.work_once()
        assert result["status"] == "failed"
        assert "unknown job kind" in result["error"]


def test_cli_shards_enqueue_and_work(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    db, host_a = _seed_shard_db(tmp_path)
    monkeypatch.setenv("AIOS_SHARDS_DB", db)
    main(["shards", "enqueue", "--profile", "instagram:main",
          "--kind", "autopilot", "--payload", '{"args": ["--max", "3"]}'])
    out = json.loads(capsys.readouterr().out)
    assert out["enqueued"] >= 1 and out["kind"] == "autopilot"

    main(["shards", "jobs", "--status", "pending"])
    pending = json.loads(capsys.readouterr().out)
    assert pending[0]["profile_key"] == "instagram:main"

    # Рабочий процесс чужой ноды — честный idle:
    other = "worker-1" if host_a == "worker-2" else "worker-2"
    main(["shards", "work", "--host", other, "--once"])
    idle = json.loads(capsys.readouterr().out)
    assert idle["status"] == "idle"

    # Своя нода исполняет: handle без subprocess — через инъекцию нельзя,
    # поэтому проверяем claim-часть через API worker'а:
    from aios_core.platforms.shardexec import ShardJobs as _Jobs
    with _Jobs(db) as jobs:
        claimed = jobs.claim_next(host_a)
        assert claimed is not None and claimed["kind"] == "autopilot"
        jobs.complete(claimed["id"], ok=True,
                      result={"code": 0, "simulated": True})
    main(["shards", "jobs", "--status", "done"])
    done = json.loads(capsys.readouterr().out)
    assert done[0]["result"]["simulated"] is True


def test_cli_autopilot_job_handler_uses_subprocess(tmp_path, monkeypatch):
    from aios_core.platforms import shardexec

    ran = []

    class _Proc:
        returncode = 0
        stdout = '{"steps": {}}'

        def __init__(self, cmd, **kwargs):
            ran.append(cmd)

    monkeypatch.setattr(shardexec.subprocess, "run", _Proc)
    handlers = shardexec.default_handlers(cli_path=str(tmp_path))
    result = handlers["autopilot"]("instagram:main", {"args": ["--max", "2"]})
    assert result["code"] == 0
    assert any("autopilot" in part for part in ran[0])
    assert any("instagram-main.sqlite" in part for part in ran[0])
    with pytest.raises(ValueError, match="instagram"):
        handlers["autopilot"]("olx:main", {})
