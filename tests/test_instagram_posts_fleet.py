"""Tests for Instagram own-posts (parser + guarded composer), the video-card
extractor and the FleetScheduler pool-balanced job runner."""

import json
import os
from pathlib import Path

import pytest
import yaml

from aios_core.platforms import DevicePool, FleetScheduler, HintVideoParser
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms import video_parser_for
from aios_core.platforms.videocards import VideoCard, parse_counter_text

REELS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/reel_card">
    <node text="Огляд нових кросівок від нашого магазину" resource-id=""/>
    <node text="0:32" resource-id=""/>
    <node text="12 340 переглядів" resource-id=""/>
    <node text="543 вподобання" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/reel_card">
    <node text="Розпакування сумки" resource-id=""/>
    <node text="1:05" resource-id=""/>
    <node text="2 001 view" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/reel_card">
    <node text="" resource-id=""/>
  </node>
</hierarchy>
"""

# ---------------------------------------------------------------------------
# VideoCards
# ---------------------------------------------------------------------------


def test_parse_counter_text_units():
    assert parse_counter_text("12 340 переглядів") == ("views", 12340)
    assert parse_counter_text("543 вподобання") == ("likes", 543)
    assert parse_counter_text("2 001 view") == ("views", 2001)
    assert parse_counter_text("7 likes") == ("likes", 7)
    assert parse_counter_text("Не число") is None


def test_hint_video_parser_cards():
    cards = HintVideoParser().parse(REELS_XML, query="cross")
    assert len(cards) == 2
    first, second = cards
    assert first.title == "Огляд нових кросівок від нашого магазину"
    assert first.duration == "0:32"
    assert first.views == 12340
    assert first.likes == 543
    assert first.marker == "com.instagram.android:id/reel_card"
    assert first.fingerprint == VideoCard(title=first.title, duration="0:32").fingerprint
    assert second.views == 2001 and second.likes is None
    payload = first.to_dict()
    assert payload["query"] == "cross"


def test_hint_video_parser_custom_markers_and_empty():
    parser = HintVideoParser(video_markers=["shop_reel"])
    assert parser.markers == ("shop_reel",)
    assert parser.parse(REELS_XML) == []  # маркер не совпал
    assert HintVideoParser(video_markers=[]).markers == ("reel", "video", "clips")  # пусто → дефолт


def test_video_parser_for_descriptor(tmp_path):
    (tmp_path / "instagram.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "instagram",
                "android_package": "com.instagram.android",
                "extras": {
                    "parser_hints": {
                        "content_categories": {
                            "video_markers": ["com.instagram.android:id/clip_tile"],
                            "story_markers": [],
                            "duration_labels": 0,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    parser = video_parser_for("instagram", directory=str(tmp_path))
    assert parser.markers == ("clip_tile",)


# ---------------------------------------------------------------------------
# Instagram own posts
# ---------------------------------------------------------------------------

GRID_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/row_profile_grid_item">
    <node text="Наші нові кросівки" resource-id=""/>
    <node text="1 234 перегляди" resource-id=""/>
    <node text="56 вподобань" resource-id=""/>
    <node text="12 коментарів" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/row_profile_grid_item">
    <node text="Сумка в наявності" resource-id=""/>
    <node text="88 likes" resource-id=""/>
  </node>
</hierarchy>
"""


class _ADB:
    package = "com.instagram.android"

    def __init__(self, dumps=(), adb_prefix="adb"):
        self.dumps = list(dumps)
        self.calls = []
        self._prefix = adb_prefix

    @property
    def adb(self):
        return self._prefix

    def run(self, command):
        self.calls.append(command)
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename):
        if not self.dumps:
            return {"code": 1, "stdout": "", "stderr": "no dumps"}
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}

    def tap(self, x, y):
        self.calls.append(("tap", x, y))
        return {"code": 0, "stdout": "", "stderr": ""}

    def input_text(self, text):
        self.calls.append(("input_text", text))
        return {"code": 0, "stdout": "", "stderr": ""}


def test_own_posts_parser_counters_and_own_ad_mapping():
    from aios_core.modules.instagram import OwnPostsParser

    posts = OwnPostsParser().parse(GRID_XML)
    assert len(posts) == 2
    first, second = posts
    assert first.caption == "Наші нові кросівки"
    assert (first.views, first.likes, first.comments) == (1234, 56, 12)
    own_ad = first.to_own_ad()
    assert own_ad.title == "Наші нові кросівки"
    assert own_ad.views == 1234
    assert own_ad.favorites == 56 and own_ad.messages == 12
    assert second.likes == 88 and second.views == 0
    assert first.fingerprint != second.fingerprint
    assert posts[0].to_dict()["fingerprint"] == first.fingerprint


NEXT_XML = (
    '<hierarchy><node text="Next" '
    'resource-id="com.instagram.android:id/next_button" '
    'bounds="[400,100][680,200]"/></hierarchy>'
)
SHARE_XML = (
    '<hierarchy><node text="Share" '
    'resource-id="com.instagram.android:id/share_button" '
    'bounds="[400,100][680,200]"/></hierarchy>'
)
PLAIN_XML = '<hierarchy><node text="Stories" resource-id="x"/></hierarchy>'


def test_post_composer_dry_run_default_touches_nothing():
    from aios_core.modules.instagram import PostComposer

    adb = _ADB()
    result = PostComposer(adb=adb, wait_s=0).publish(
        "post.jpg",
        "Нові кросівки в наявності!",
    )
    assert result["status"] == "dry-run"
    assert any("push post.jpg" in step for step in result["plan"])
    assert adb.calls == []  # устройство не тронуто
    with pytest.raises(ValueError, match="empty caption"):
        PostComposer(adb=adb, wait_s=0).publish("post.jpg", "   ")


def test_post_composer_confirm_full_flow(tmp_path):
    from aios_core.modules.instagram import PostComposer

    image = tmp_path / "post.jpg"
    image.write_bytes(b"jpeg-bytes")
    adb = _ADB([NEXT_XML, SHARE_XML], adb_prefix="adb -s emulator-5557")
    result = PostComposer(adb=adb, wait_s=0).publish(
        str(image),
        "Нові кросівки!",
        confirm=True,
    )
    assert result["status"] == "published"
    actions = [step["action"] for step in result["steps"]]
    assert actions == ["push", "open_create", "tap_next", "input_caption", "tap_share"]
    assert any(
        "instagram://library" in c and "adb -s emulator-5557" in c
        for c in adb.calls
        if isinstance(c, str)
    )
    assert any(
        "push" in c and "/sdcard/aios_post_input.jpg" in c for c in adb.calls if isinstance(c, str)
    )
    assert ("input_text", "Нові кросівки!") in adb.calls
    assert adb.calls.count(("tap", 540, 150)) == 2


def test_post_composer_confirm_honest_errors(tmp_path):
    from aios_core.modules.instagram import PostComposer

    with pytest.raises(ValueError, match="image not found"):
        PostComposer(adb=_ADB(), wait_s=0).publish(
            "/nope.jpg",
            "caption",
            confirm=True,
        )

    image = tmp_path / "post.jpg"
    image.write_bytes(b"x")
    adb = _ADB([PLAIN_XML])  # кнопки Next на экране нет
    result = PostComposer(adb=adb, wait_s=0).publish(
        str(image),
        "caption",
        confirm=True,
    )
    assert result["status"] == "error"
    assert "layout drift" in result["error"]


# ---------------------------------------------------------------------------
# FleetScheduler
# ---------------------------------------------------------------------------


def _jobs():
    return [
        {"platform": "instagram", "profile": "main", "every_s": 60},
        {"platform": "olx", "profile": "work", "every_s": 60},
    ]


def test_fleet_due_jobs_and_busy_pool():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-1", avd_name="a1")
        scheduler = FleetScheduler(pool)
        runs = []

        def runner(platform, profile, serial=None):
            runs.append((platform, profile, serial))
            return {"ok": True}

        # Устройство держит сторонний процесс → честный skipped-busy,
        # last_run не трогаем:
        pool.lease("external:holder")
        manifest = scheduler.run_due(_jobs(), runner=runner)
        assert manifest["ran"] == 0
        assert manifest["skipped_busy"] == 2
        assert runs == []
        assert len(scheduler.due_jobs(_jobs())) == 2

        # Освободили — оба джоба идут по очереди на одном устройстве:
        pool.release("external:holder")
        manifest = scheduler.run_due(_jobs(), runner=runner)
        assert manifest["ran"] == 2
        assert runs[0][2] == "emulator-1" == runs[1][2]
        assert pool.get("emulator-1")["status"] == "idle"  # release был

        # Интервалы не истекли → по второму кругу ничего не due:
        assert scheduler.due_jobs(_jobs()) == []


def test_fleet_drift_alert_and_error_isolation():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-1", avd_name="a1")
        pool.register("emulator-2", avd_name="a2")
        posted = []

        def poster(url, payload):
            posted.append({"url": url, "payload": payload})
            return True

        from aios_core.modules.olx.notifier import WebhookNotifier

        scheduler = FleetScheduler(
            pool,
            notifier=WebhookNotifier(
                url="http://hook",
                poster=poster,
            ),
        )

        def drifting(platform, profile, serial=None):
            if platform == "instagram":
                return {"marker_status": "drift"}
            raise RuntimeError("boom")

        manifest = scheduler.run_due(_jobs(), runner=drifting)
        assert manifest["drifts"] == 1
        assert manifest["errors"] == 1
        assert posted[0]["payload"]["event"] == "marker-drift"
        assert posted[0]["payload"]["data"]["platform"] == "instagram"
        # Оба устройства свободны после цикла (error не утекает lease):
        assert all(d["status"] == "idle" for d in pool.status())


def test_fleet_error_releases_device():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-1", avd_name="a1")
        scheduler = FleetScheduler(pool)

        def broken(platform, profile, serial=None):
            raise RuntimeError("adb gone")

        manifest = scheduler.run_due(_jobs(), runner=broken)
        statuses = {r["job"]: r["status"] for r in manifest["results"]}
        assert "error" in statuses.values()
        assert pool.get("emulator-1")["status"] == "idle"


# ---------------------------------------------------------------------------
# CLI instagram own/post + devices fleet-run
# ---------------------------------------------------------------------------


def test_cli_instagram_own_snapshot_and_post_dry_run(tmp_path, capsys):
    from aios_cli import main

    dump = tmp_path / "grid.xml"
    dump.write_text(GRID_XML, encoding="utf-8")
    db = str(tmp_path / "ig.sqlite")
    main(["instagram", "own", "--db", db, "--dump", str(dump)])
    out = json.loads(capsys.readouterr().out)
    assert out["recorded"] == 2 and out["new"] == 2
    assert out["posts"][0]["caption"] == "Наші нові кросівки"

    main(["instagram", "post", "--image", "post.jpg", "--text", "Нові кросівки в наявності!"])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "dry-run"
    assert any("input caption" in step for step in out["plan"])

    main(["instagram", "post", "--image", "/nope.jpg", "--text", "caption", "--confirm"])
    out = json.loads(capsys.readouterr().out)
    assert "image not found" in out["error"]


def test_cli_devices_fleet_run(tmp_path, capsys, monkeypatch):
    from aios_cli import main
    from aios_core.platforms import DevicePool, Profile, ProfileStore, load_catalog_file

    load_catalog_file("platforms/instagram.yaml")
    try:
        devices_db = tmp_path / "devices.sqlite"
        profiles_db = tmp_path / "profiles.sqlite"
        with DevicePool(str(devices_db)) as pool:
            pool.register("emulator-1", avd_name="a1")
        store = ProfileStore(str(profiles_db))
        store.add(
            Profile(
                platform="instagram",
                name="main",
                is_default=True,
                db_path=str(tmp_path / "ig.sqlite"),
            )
        )
        store.close()
        monkeypatch.setenv("AIOS_DEVICES_DB", str(devices_db))
        monkeypatch.setenv("AIOS_PROFILES_DB", str(profiles_db))
        ProfileStore.reset_default()

        main(["devices", "fleet-run"])
        out = json.loads(capsys.readouterr().out)
        assert out["ran"] == 1
        assert out["results"][0]["job"] == "instagram:main"
        assert out["results"][0]["serial"] == "emulator-1"

        # Интервал не истёк → ничего не due:
        main(["devices", "fleet-run"])
        out = json.loads(capsys.readouterr().out)
        assert out["ran"] == 0 and out["results"] == []
    finally:
        descriptor_mod._PLATFORMS.pop("instagram", None)
        ProfileStore.reset_default()
