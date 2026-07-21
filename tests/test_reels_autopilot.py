"""Tests for the Reels scroll-cycle collector (reelscout), the Instagram
``autopilot`` CLI cycle, and the multi-account waitlist e2e sequencing.
"""

import json
from pathlib import Path

import pytest
import yaml

from aios_core.modules.instagram import InstagramStorage
from aios_core.modules.olx.adb import ADBController
from aios_core.platforms import (
    DevicePool,
    FleetScheduler,
    HintVideoParser,
    PlatformDescriptor,
    ReelsCollector,
    get_platform,
    load_catalog_file,
)
from aios_core.platforms import descriptor as descriptor_mod

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FEED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Кросівки Nike Air нові" resource-id=""/>
    <node text="3 200 грн" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Сумка шкіряна" resource-id=""/>
    <node text="1 850 грн" resource-id=""/>
  </node>
</hierarchy>
"""

EMPTY_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"

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


def _reels(*titles):
    """Reels-дамп: одна видео-карточка на каждый title."""
    nodes = "\n".join(
        '  <node text="" resource-id="com.instagram.android:id/reel_card">\n'
        f'    <node text="{title}" resource-id=""/>\n'
        '    <node text="0:15" resource-id=""/>\n'
        '    <node text="100 переглядів" resource-id=""/>\n'
        "  </node>"
        for title in titles
    )
    return f"<hierarchy>\n{nodes}\n</hierarchy>"


class _ADB:
    """Fake-ADB: очередь дампов + журнал вызовов."""

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


def _descriptor():
    return PlatformDescriptor(
        name="instagram",
        android_package="com.instagram.android",
        agent_module="aios_core.modules.instagram",
    )


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
    loaded = load_catalog_file("platforms/instagram.yaml")
    yield loaded[0]
    descriptor_mod._PLATFORMS.pop(loaded[0].name, None)


# ---------------------------------------------------------------------------
# ReelsCollector — scroll-цикл
# ---------------------------------------------------------------------------

def test_reels_scroll_cycle_dedup_and_stop():
    adb = _ADB([_reels("A", "B"), _reels("B", "C"), _reels("C")])
    collector = ReelsCollector(
        _descriptor(), adb=adb, parser=HintVideoParser(["reel_card"]),
    )
    cards = collector.collect()
    assert [c.title for c in cards] == ["A", "B", "C"]
    swipes = [c for c in adb.calls if isinstance(c, tuple) and c[0] == "swipe"]
    assert len(swipes) == 2  # три дампа = два свайпа, стоп по пустому


def test_reels_max_cards_cap_and_no_swipe():
    adb = _ADB([_reels("A", "B", "C", "D")])
    collector = ReelsCollector(
        _descriptor(), adb=adb, parser=HintVideoParser(["reel_card"]),
    )
    cards = collector.collect(max_cards=2)
    assert [c.title for c in cards] == ["A", "B"]
    assert not [c for c in adb.calls
                if isinstance(c, tuple) and c[0] == "swipe"]


def test_reels_max_swipes_cap():
    feeds = [_reels(f"V{i}") for i in range(10)]
    adb = _ADB(feeds)
    collector = ReelsCollector(
        _descriptor(), adb=adb, parser=HintVideoParser(["reel_card"]),
    )
    cards = collector.collect(max_cards=100, max_swipes=2, stop_after_empty=9)
    assert [c.title for c in cards] == ["V0", "V1", "V2"]  # 3 дампа, 2 свайпа


def test_reels_empty_device_is_honest_empty():
    collector = ReelsCollector(
        _descriptor(), adb=_ADB([]), parser=HintVideoParser(["reel_card"]),
    )
    assert collector.collect() == []


def test_reels_driver_gate():
    collector = ReelsCollector(
        _descriptor(), adb=_ADB([_reels("A")]),
        parser=HintVideoParser(["reel_card"]),
        driver=lambda adb: False,
    )
    with pytest.raises(RuntimeError, match="видео-ленту"):
        collector.collect()
    opened = []
    collector = ReelsCollector(
        _descriptor(), adb=_ADB([_reels("A"), EMPTY_XML]),
        parser=HintVideoParser(["reel_card"]),
        driver=lambda adb: opened.append(True) or True,
    )
    assert [c.title for c in collector.collect()] == ["A"]
    assert opened == [True]


def test_reels_resolve_parser_recipe_errors(tmp_path):
    collector = ReelsCollector(_descriptor(), adb=_ADB(),
                               directory=str(tmp_path))
    with pytest.raises(ValueError, match="не найден"):
        collector.resolve_parser()


def test_reels_parser_from_yaml_hints(tmp_path):
    _write_yaml(tmp_path, {"content_categories": {
        "video_markers": ["com.instagram.android:id/reel_card"],
    }})
    collector = ReelsCollector(
        _descriptor(), adb=_ADB([_reels("FromYaml"), EMPTY_XML]),
        directory=str(tmp_path),
    )
    assert [c.title for c in collector.collect()] == ["FromYaml"]


def test_reels_collect_to_storage_dedup_between_cycles():
    storage = InstagramStorage(":memory:")
    adb = _ADB([_reels("R1", "R2"), EMPTY_XML])
    collector = ReelsCollector(
        _descriptor(), adb=adb, parser=HintVideoParser(["reel_card"]),
    )
    written, cards = collector.collect_to_storage(storage, query="reels")
    assert written == 2 and len(cards) == 2
    assert storage.seen_count(kind="video") == 2
    # Повторный цикл с теми же карточками — ничего нового:
    adb2 = _ADB([_reels("R1", "R2"), EMPTY_XML])
    collector2 = ReelsCollector(
        _descriptor(), adb=adb2, parser=HintVideoParser(["reel_card"]),
    )
    written2, _ = collector2.collect_to_storage(storage, query="reels")
    assert written2 == 0
    assert storage.seen_count() == 2  # ad-kind не задет
    storage.close()


def test_storage_check_and_record_semantics():
    storage = InstagramStorage(":memory:")
    assert storage.check_and_record("fp1", kind="video", ref="reels") is True
    assert storage.check_and_record("fp1", kind="video") is False
    assert storage.check_and_record("fp1", kind="event") is True  # другой kind
    assert storage.check_and_record("") is False
    assert storage.seen_count() == 2
    assert storage.seen_count(kind="video") == 1
    storage.close()


# ---------------------------------------------------------------------------
# CLI: instagram reels / autopilot
# ---------------------------------------------------------------------------

def _patch_adb(monkeypatch, fake):
    from aios_core.modules.olx import adb as adb_mod
    monkeypatch.setattr(
        adb_mod, "ADBController", lambda *args, **kwargs: fake,
    )


def test_cli_instagram_reels(tmp_path, capsys, monkeypatch,
                             instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {})
    db = tmp_path / "ig.sqlite"
    _patch_adb(monkeypatch, _ADB([_reels("X1", "X2"), EMPTY_XML]))
    main(["instagram", "reels", "--db", str(db), "--max", "10",
          "--directory", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["new"] == 2 and out["seen"] == 2
    assert out["cards"][0]["title"] == "X1"

    # Повторный запуск по той же ленте — дедуп по квитанциям:
    _patch_adb(monkeypatch, _ADB([_reels("X1", "X2"), EMPTY_XML]))
    main(["instagram", "reels", "--db", str(db), "--max", "10",
          "--directory", str(tmp_path)])
    out2 = json.loads(capsys.readouterr().out)
    assert out2["new"] == 0 and out2["seen"] == 2

    storage = InstagramStorage(str(db))
    assert storage.seen_count(kind="video") == 2
    storage.close()


def test_cli_instagram_autopilot_full_cycle(tmp_path, capsys, monkeypatch,
                                            instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {
        "card_markers": [
            {"resource_id": "com.instagram.android:id/shop_card"}],
    })
    db = tmp_path / "ig.sqlite"
    # Одобренный ответ ждёт flush:
    storage = InstagramStorage(str(db))
    storage.enqueue_outbox("chat:anna", "Добрий день, актуально!")
    storage.close()

    fake = _ADB([FEED_XML, _reels("R1", "R2"), EMPTY_XML, CHAT_XML])
    _patch_adb(monkeypatch, fake)
    main(["instagram", "autopilot", "--db", str(db), "--max", "2",
          "--reels-max", "50", "--directory", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    steps = out["steps"]
    assert steps["collect"]["inserted"] == 2
    assert steps["reels"]["new"] == 2
    assert steps["dm_flush"] == [{"id": 1, "status": "sent"}]
    assert "post" not in steps  # без --post-image шага нет
    # Текст реально дошёл до устройства через HintSender:
    assert ("input_text", "Добрий день, актуально!") in fake.calls
    assert any(c == ("tap", 990, 2250) for c in fake.calls
               if isinstance(c, tuple))

    # Повтор: collect/reels дают ноль нового (дедуп), outbox пуст:
    fake2 = _ADB([FEED_XML, _reels("R1", "R2"), EMPTY_XML])
    _patch_adb(monkeypatch, fake2)
    main(["instagram", "autopilot", "--db", str(db), "--max", "2",
          "--reels-max", "50", "--directory", str(tmp_path)])
    out2 = json.loads(capsys.readouterr().out)
    assert out2["steps"]["collect"]["inserted"] == 0
    assert out2["steps"]["reels"]["new"] == 0
    assert out2["steps"]["dm_flush"] == []


def test_cli_instagram_autopilot_post_dry_run(tmp_path, capsys, monkeypatch,
                                              instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {
        "card_markers": [
            {"resource_id": "com.instagram.android:id/shop_card"}],
    })
    db = tmp_path / "ig.sqlite"
    fake = _ADB([FEED_XML, _reels("R1"), EMPTY_XML])
    _patch_adb(monkeypatch, fake)
    main(["instagram", "autopilot", "--db", str(db), "--max", "2",
          "--directory", str(tmp_path),
          "--post-image", "post.jpg", "--post-text", "Нові кросівки!"])
    out = json.loads(capsys.readouterr().out)
    post = out["steps"]["post"]
    assert post["status"] == "dry-run"  # guarded: без --confirm молчим
    assert any("post.jpg" in step for step in post["plan"])
    assert not [c for c in fake.calls
                if isinstance(c, str) and "push" in c]


# ---------------------------------------------------------------------------
# Multi-account e2e: два Instagram-профиля через waitlist на одной ноде
# ---------------------------------------------------------------------------

def test_multi_account_instagram_waitlist_e2e():
    clock = [1_000.0]
    jobs = [
        {"platform": "instagram", "profile": "acc_a", "every_s": 60},
        {"platform": "instagram", "profile": "acc_b", "every_s": 60},
    ]
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5554", avd_name="ig-one")
        scheduler = FleetScheduler(pool, now=lambda: clock[0])
        runs = []

        def runner(platform, profile, serial=None):
            runs.append((profile, serial))
            return {"ok": True}

        # Устройство занято внешним процессом → оба аккаунта ждут (waitlist):
        pool.lease("external:blocker")
        manifest = scheduler.run_due(jobs, runner=runner)
        assert manifest["skipped_busy"] == 2 and runs == []

        # Освободили — оба профиля отработали последовательно на одной ноде:
        pool.release("external:blocker")
        manifest = scheduler.run_due(jobs, runner=runner)
        assert manifest["ran"] == 2
        assert [profile for profile, _ in runs] == ["acc_a", "acc_b"]
        assert all(serial == "emulator-5554" for _, serial in runs)
        # last_run — раздельно на профиль:
        assert int(pool.limit("fleet:last_run:instagram:acc_a") or 0) == 1000
        assert int(pool.limit("fleet:last_run:instagram:acc_b") or 0) == 1000

        # Интервал не истёк → никто не due; после истечения — оба снова:
        assert scheduler.due_jobs(jobs) == []
        clock[0] += 61
        assert len(scheduler.due_jobs(jobs)) == 2
        manifest = scheduler.run_due(jobs, runner=runner)
        assert manifest["ran"] == 2
        assert [profile for profile, _ in runs[-2:]] == ["acc_a", "acc_b"]


def test_cron_plan_instagram_autopilot_line(tmp_path, capsys, monkeypatch):
    from aios_cli import main
    from aios_core.platforms import Profile, ProfileStore

    profiles_db = tmp_path / "profiles.sqlite"
    store = ProfileStore(str(profiles_db))
    store.add(Profile(platform="instagram", name="main", is_default=True,
                      db_path=str(tmp_path / "ig.sqlite")))
    store.close()
    monkeypatch.setenv("AIOS_PROFILES_DB", str(profiles_db))
    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    ProfileStore.reset_default()

    main(["cron-plan", "--platform", "instagram"])
    plan = capsys.readouterr().out
    assert "instagram autopilot --login" in plan
    assert "instagram-main.sqlite" in plan
