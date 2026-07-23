"""Tests for the calibrated Reels-tab driver, video-new webhook alerts,
and multi-host (shard-mapped) cron plans.
"""

import json
from pathlib import Path

import pytest
import yaml

from aios_core.modules.instagram import InstagramStorage
from aios_core.platforms import (
    PlatformDescriptor,
    ReelsCollector,
    ReelsTabDriver,
    ShardRouter,
    get_platform,
    load_catalog_file,
    reels_driver_for,
)
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms.videocards import HintVideoParser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HOME_TAB_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" content-desc="Reels"
        resource-id="com.instagram.android:id/reels_tab"
        bounds="[540,2300][810,2400]"/>
  <node text="Home" resource-id="com.instagram.android:id/home_tab"
        bounds="[0,2300][270,2400]"/>
</hierarchy>
"""

HOME_TEXT_TAB_XML = """<hierarchy>
  <node text="Reels" content-desc="" resource-id=""
        bounds="[540,2300][810,2400]"/>
</hierarchy>"""

HOME_NO_TAB_XML = """<hierarchy>
  <node text="Home" resource-id="com.instagram.android:id/home_tab"
        bounds="[0,2300][270,2400]"/>
</hierarchy>"""

EMPTY_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"


def _reels(*titles):
    nodes = "\n".join(
        '  <node text="" resource-id="com.instagram.android:id/reel_card">\n'
        f'    <node text="{title}" resource-id=""/>\n'
        '    <node text="0:15" resource-id=""/>\n'
        "  </node>"
        for title in titles
    )
    return f"<hierarchy>\n{nodes}\n</hierarchy>"


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


def _descriptor():
    return PlatformDescriptor(
        name="instagram",
        android_package="com.instagram.android",
        agent_module="aios_core.modules.instagram",
    )


@pytest.fixture
def instagram_registered():
    loaded = load_catalog_file("platforms/instagram.yaml")
    yield loaded[0]
    descriptor_mod._PLATFORMS.pop(loaded[0].name, None)


# ---------------------------------------------------------------------------
# ReelsTabDriver
# ---------------------------------------------------------------------------


def test_tab_driver_taps_reels_tab_center():
    adb = _ADB([HOME_TAB_XML])
    slept = []
    driver = ReelsTabDriver(adb=adb, open_wait_s=0.7, sleeper=slept.append)
    assert driver.drive() is True
    assert ("tap", 675, 2350) in adb.calls  # центр bounds вкладки
    assert slept == [0.7]


def test_tab_driver_text_marker_match():
    adb = _ADB([HOME_TEXT_TAB_XML])
    driver = ReelsTabDriver(adb=adb, open_wait_s=0, sleeper=lambda s: None)
    assert driver.drive() is True
    assert ("tap", 675, 2350) in adb.calls


def test_tab_driver_missing_tab_is_honest_false():
    adb = _ADB([HOME_NO_TAB_XML])
    driver = ReelsTabDriver(adb=adb, open_wait_s=0, sleeper=lambda s: None)
    assert driver.drive() is False
    assert not [c for c in adb.calls if isinstance(c, tuple) and c[0] == "tap"]


def test_tab_driver_no_dump_is_false():
    driver = ReelsTabDriver(adb=_ADB([]), open_wait_s=0, sleeper=lambda s: None)
    assert driver.drive() is False


def test_reels_driver_for_yaml_and_defaults(tmp_path):
    (tmp_path / "instagram.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "instagram",
                "android_package": "com.instagram.android",
                "extras": {
                    "parser_hints": {
                        "navigation": {
                            "reels_tab": {
                                "rid_markers": [
                                    {"resource_id": "com.instagram.android:id/video_tab"}
                                ],
                                "text_markers": ["Кліпси"],
                            }
                        }
                    }
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    driver = reels_driver_for("instagram", adb=_ADB([]), directory=str(tmp_path))
    assert driver.rid_markers == ("video_tab",)
    assert driver.text_markers == ("кліпси",)


def test_reels_driver_for_defaults_without_section(tmp_path):
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
    driver = reels_driver_for("instagram", adb=_ADB([]), directory=str(tmp_path))
    assert "reels_tab" in driver.rid_markers
    assert "reels" in driver.text_markers
    with pytest.raises(ValueError, match="descriptor not found"):
        reels_driver_for("ghost", directory=str(tmp_path))


def test_tab_driver_integrates_with_collector():
    adb = _ADB([HOME_TAB_XML, _reels("R1"), EMPTY_XML])
    collector = ReelsCollector(
        _descriptor(),
        adb=adb,
        parser=HintVideoParser(["reel_card"]),
        driver=ReelsTabDriver(open_wait_s=0, sleeper=lambda s: None).drive,
    )
    assert [c.title for c in collector.collect()] == ["R1"]
    assert ("tap", 675, 2350) in adb.calls


def test_tab_driver_failure_blocks_cycle():
    collector = ReelsCollector(
        _descriptor(),
        adb=_ADB([HOME_NO_TAB_XML]),
        parser=HintVideoParser(["reel_card"]),
        driver=ReelsTabDriver(open_wait_s=0, sleeper=lambda s: None).drive,
    )
    with pytest.raises(RuntimeError, match="видео-ленту"):
        collector.collect()


# ---------------------------------------------------------------------------
# Video-new webhook alerts
# ---------------------------------------------------------------------------


def test_video_new_alert_on_new_cards_only():
    storage = InstagramStorage(":memory:")
    notifier = _Notifier()
    collector = ReelsCollector(
        _descriptor(),
        adb=_ADB([_reels("N1", "N2"), EMPTY_XML]),
        parser=HintVideoParser(["reel_card"]),
        notifier=notifier,
    )
    written, _ = collector.collect_to_storage(storage, query="reels")
    assert written == 2
    assert len(notifier.events) == 1
    event, data = notifier.events[0]
    assert event == "video-new"
    assert data["platform"] == "instagram"
    assert data["new"] == 2 and data["seen"] == 2
    assert data["sample"] == ["N1", "N2"]

    # Повторный цикл без новых — алёрта нет:
    collector2 = ReelsCollector(
        _descriptor(),
        adb=_ADB([_reels("N1", "N2"), EMPTY_XML]),
        parser=HintVideoParser(["reel_card"]),
        notifier=notifier,
    )
    written2, _ = collector2.collect_to_storage(storage, query="reels")
    assert written2 == 0 and len(notifier.events) == 1
    storage.close()


# ---------------------------------------------------------------------------
# CLI: reels/autopilot с --open-tab и --webhook
# ---------------------------------------------------------------------------


def _patch_adb(monkeypatch, fake):
    from aios_core.modules.olx import adb as adb_mod

    monkeypatch.setattr(
        adb_mod,
        "ADBController",
        lambda *args, **kwargs: fake,
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
    path.write_text(
        yaml.safe_dump(
            {
                "name": "instagram",
                "android_package": "com.instagram.android",
                "extras": {"parser_hints": hints},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


FEED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Кросівки Nike Air" resource-id=""/>
    <node text="3 200 грн" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Сумка шкіряна" resource-id=""/>
    <node text="1 850 грн" resource-id=""/>
  </node>
</hierarchy>
"""


def test_cli_reels_open_tab_and_webhook(tmp_path, capsys, monkeypatch, instagram_registered):
    from aios_cli import main

    _write_yaml(tmp_path, {})
    db = tmp_path / "ig.sqlite"
    recorder = _Notifier()
    fake = _ADB([HOME_TAB_XML, _reels("W1", "W2"), EMPTY_XML])
    _patch_adb(monkeypatch, fake)
    _patch_notifier(monkeypatch, recorder)
    monkeypatch.setattr(
        "aios_core.platforms.reelscout.time.sleep",
        lambda s: None,
    )
    main(
        [
            "instagram",
            "reels",
            "--db",
            str(db),
            "--max",
            "10",
            "--directory",
            str(tmp_path),
            "--open-tab",
            "--webhook",
            "http://hook.example/in",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert out["open_tab"] is True and out["notified"] is True
    assert out["new"] == 2
    assert ("tap", 675, 2350) in fake.calls  # вкладка тапнута до цикла
    assert recorder.events[0][0] == "http://hook.example/in"
    assert recorder.events[0][1] == "video-new"


def test_cli_reels_open_tab_missing_tab_reports_error(
    tmp_path, capsys, monkeypatch, instagram_registered
):
    from aios_cli import main

    _write_yaml(tmp_path, {})
    _patch_adb(monkeypatch, _ADB([HOME_NO_TAB_XML]))
    monkeypatch.setattr(
        "aios_core.platforms.reelscout.time.sleep",
        lambda s: None,
    )
    main(
        [
            "instagram",
            "reels",
            "--db",
            str(tmp_path / "ig.sqlite"),
            "--directory",
            str(tmp_path),
            "--open-tab",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert "error" in out and "видео-ленту" in out["error"]


def test_cli_autopilot_open_tab_and_webhook(tmp_path, capsys, monkeypatch, instagram_registered):
    from aios_cli import main

    _write_yaml(
        tmp_path,
        {
            "card_markers": [{"resource_id": "com.instagram.android:id/shop_card"}],
        },
    )
    db = tmp_path / "ig.sqlite"
    recorder = _Notifier()
    fake = _ADB([FEED_XML, HOME_TAB_XML, _reels("P1"), EMPTY_XML])
    _patch_adb(monkeypatch, fake)
    _patch_notifier(monkeypatch, recorder)
    monkeypatch.setattr(
        "aios_core.platforms.reelscout.time.sleep",
        lambda s: None,
    )
    main(
        [
            "instagram",
            "autopilot",
            "--db",
            str(db),
            "--max",
            "2",
            "--reels-max",
            "50",
            "--directory",
            str(tmp_path),
            "--open-tab",
            "--webhook",
            "http://hook/in",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert out["steps"]["collect"]["inserted"] == 2
    assert out["steps"]["reels"]["new"] == 1
    assert out["steps"]["reels"]["open_tab"] is True
    assert out["steps"]["reels"]["notified"] is True
    assert recorder.events[0][1] == "video-new"


# ---------------------------------------------------------------------------
# Multi-host cron-plan (--shard-map)
# ---------------------------------------------------------------------------


def _seed_profiles(tmp_path, monkeypatch, *pairs):
    from aios_core.platforms import Profile, ProfileStore

    profiles_db = tmp_path / "profiles.sqlite"
    store = ProfileStore(str(profiles_db))
    for platform, name in pairs:
        store.add(
            Profile(
                platform=platform,
                name=name,
                is_default=True,
                db_path=str(tmp_path / f"{name}.sqlite"),
            )
        )
    store.close()
    monkeypatch.setenv("AIOS_PROFILES_DB", str(profiles_db))
    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    ProfileStore.reset_default()


def test_cron_plan_shard_map_groups_by_host(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    _seed_profiles(
        tmp_path,
        monkeypatch,
        ("instagram", "main"),
        ("instagram", "backup"),
        ("tiktok", "fun"),
    )
    shards_db = tmp_path / "shards.sqlite"
    router = ShardRouter(str(shards_db))
    router.add_host("worker-1", "http://10.0.0.1:8001")
    router.add_host("worker-2", "http://10.0.0.2:8001")
    expected = router.route_for("instagram:main")["host"]
    router.close()
    monkeypatch.setenv("AIOS_SHARDS_DB", str(shards_db))

    main(["cron-plan", "--platform", "instagram", "--shard-map"])
    plan = capsys.readouterr().out
    assert "# === host:" in plan
    # Строка autopilot профиля main — под заголовком его sticky-хоста:
    lines = plan.splitlines()
    auto_idx = next(
        i
        for i, line in enumerate(lines)
        if "instagram autopilot" in line and "instagram-main" in line
    )
    header = next(lines[i] for i in range(auto_idx, -1, -1) if lines[i].startswith("# === host:"))
    assert f"host: {expected}" in header
    assert "pool monitor — запускать на каждом хосте" in plan


def test_cron_plan_shard_map_no_hosts_local_group(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    _seed_profiles(tmp_path, monkeypatch, ("instagram", "main"))
    monkeypatch.setenv("AIOS_SHARDS_DB", str(tmp_path / "shards.sqlite"))

    main(["cron-plan", "--platform", "instagram", "--shard-map"])
    plan = capsys.readouterr().out
    assert "host: local" in plan and "без маршрута" in plan
    assert "instagram autopilot --login" in plan


def test_cron_plan_without_shard_map_unchanged(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    _seed_profiles(tmp_path, monkeypatch, ("instagram", "main"))
    monkeypatch.setenv("AIOS_SHARDS_DB", str(tmp_path / "shards.sqlite"))
    main(["cron-plan", "--platform", "instagram"])
    plan = capsys.readouterr().out
    assert "# === host:" not in plan
    assert "instagram autopilot --login" in plan
