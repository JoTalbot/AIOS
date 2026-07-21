"""Tests for the generic platform AutoWatch engine, the guarded messenger
REST plane per platform, content categories in calibration and cron-plan
generic autowatch lines."""

import json
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.platforms import (
    DevicePool,
    PlatformDescriptor,
    Profile,
    ProfileStore,
    register_platform,
)
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms.autowatch import autowatch_cycle, resolve_card_parser
from aios_core.platforms.calibrate import CalibrationAdvisor

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FEED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.watch.demo:id/itemCard">
    <node text="Кросівки Nike Air нові" resource-id=""/>
    <node text="3 200 грн" resource-id=""/>
    <node text="Київ" resource-id=""/>
  </node>
  <node text="" resource-id="com.watch.demo:id/itemCard">
    <node text="Сумка шкіряна ручна робота" resource-id=""/>
    <node text="1 850 грн" resource-id=""/>
    <node text="Львів" resource-id=""/>
  </node>
</hierarchy>
"""

EMPTY_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"


class _ADB:
    package = "com.watch.demo"

    def __init__(self, dumps=()):
        self.dumps = list(dumps)
        self.calls = []

    @property
    def adb(self):
        return "adb"

    def run(self, command):
        self.calls.append(command)
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename):
        if not self.dumps:
            return {"code": 1, "stdout": "", "stderr": "no dumps"}
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}

    def swipe(self, *args, **kwargs):
        return {"code": 0, "stdout": "", "stderr": ""}


@pytest.fixture
def watch_platform(tmp_path):
    def storage_factory(db_path):
        from aios_core.modules.olx import OLXStorage
        return OLXStorage(db_path)

    def adb_factory(package, serial=None):
        from aios_core.modules.olx.adb import ADBController
        return ADBController(package=package, serial=serial)

    register_platform(PlatformDescriptor(
        name="watch-demo",
        android_package="com.watch.demo",
        agent_module="aios_core.modules.olx",  # модуль с CardParser
        storage_factory=storage_factory,
        adb_factory=adb_factory,
    ))
    store = ProfileStore(":memory:")
    store.add(Profile(
        platform="watch-demo", name="main",
        device_serial="emulator-5554",
        db_path=str(tmp_path / "watch.sqlite"), is_default=True,
    ))
    yield store
    descriptor_mod._PLATFORMS.pop("watch-demo", None)
    store.close()


def _hints_parser():
    from aios_core.platforms import build_parser
    return build_parser(CalibrationAdvisor().analyze(FEED_XML))


# ---------------------------------------------------------------------------
# resolve_card_parser chain
# ---------------------------------------------------------------------------

def test_resolve_card_parser_module_first(watch_platform):
    parser = resolve_card_parser("watch-demo")
    assert "adlisting_adgridcard" in parser.CARD_RESOURCE_MARKERS


def test_resolve_card_parser_hints_fallback(tmp_path):
    import yaml

    def storage_factory(db_path):
        from aios_core.modules.olx import OLXStorage
        return OLXStorage(db_path)

    register_platform(PlatformDescriptor(
        name="hints-only", android_package="com.hints.only",
        agent_module="no.such.module", storage_factory=storage_factory,
    ))
    try:
        hints = CalibrationAdvisor().analyze(FEED_XML)
        (tmp_path / "hints-only.yaml").write_text(yaml.safe_dump({
            "name": "hints-only", "android_package": "com.hints.only",
            "extras": {"parser_hints": hints},
        }), encoding="utf-8")
        parser = resolve_card_parser("hints-only", directory=str(tmp_path))
        assert parser.CARD_RESOURCE_MARKERS == ("itemcard",)

        (tmp_path / "hints-only.yaml").unlink()
        with pytest.raises(ValueError, match="bootup"):
            resolve_card_parser("hints-only", directory=str(tmp_path))
    finally:
        descriptor_mod._PLATFORMS.pop("hints-only", None)


# ---------------------------------------------------------------------------
# Generic AutoWatch cycle
# ---------------------------------------------------------------------------

def test_autowatch_cycle_collects_alerts_and_reports(watch_platform):
    drives = []

    def driver(package, query):
        drives.append({"package": package, "query": query})

    adb = _ADB([FEED_XML, EMPTY_XML, EMPTY_XML])
    storage_profile_db = None
    report = autowatch_cycle(
        "watch-demo", profile_name="main", queries=["кросівки"],
        store=watch_platform, adb=adb, parser=_hints_parser(),
        driver=driver, collect=True,
    )
    assert report["platform"] == "watch-demo"
    assert report["profile"] == "main"
    assert report["queries"] == ["кросівки"]
    assert report["collection"]["кросівки"]["parsed"] == 2
    assert report["collection"]["кросівки"]["inserted"] == 2
    # Новые карточки → подписка (подписок в сторадже нет → алертов 0):
    assert report["subscription_alerts"] == []
    assert report["favorite_alerts"] == []
    assert report["own_snapshot"] is None
    assert report["stagnant"] == []
    assert drives == [{"package": "com.watch.demo",
                       "query": "кросівки"}]


def test_autowatch_cycle_no_collect_is_storage_only(watch_platform):
    report = autowatch_cycle(
        "watch-demo", profile_name="main", queries=["кросівки"],
        store=watch_platform, parser=_hints_parser(), collect=False,
    )
    assert "collection" not in report
    assert report["subscription_alerts"] == []
    assert report["stagnant"] == []


def test_autowatch_unknown_platform_errors():
    with pytest.raises(ValueError, match="unknown platform"):
        autowatch_cycle("ghost-platform", queries=["q"], collect=False)


# ---------------------------------------------------------------------------
# CLI autowatch + cron-plan generic lines
# ---------------------------------------------------------------------------

def test_cli_platforms_autowatch_report(watch_platform, capsys, monkeypatch):
    from aios_cli import main

    # CLI читает ProfileStore.default() → env на файловую БД:
    file_store = str(watch_platform_path(monkeypatch, watch_platform))
    main(["platforms", "autowatch", "--platform", "watch-demo",
          "--profile", "main", "--query", "кросівки"])
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == "watch-demo"
    assert out["profile"] == "main"
    assert out["queries"] == ["кросівки"]
    # Без устройства сбор честно пуст:
    assert out["collection"]["кросівки"]["parsed"] == 0
    assert file_store

    main(["platforms", "autowatch", "--platform", "watch-demo",
          "--drive", "login"])
    out = json.loads(capsys.readouterr().out)
    assert "no login driver module" in out["error"]


def watch_platform_path(monkeypatch, store):
    """Переносит профили in-memory стора в файловый для CLI-резолвера."""
    from aios_core.platforms import ProfileStore as _Store
    import tempfile
    path = Path(tempfile.mkdtemp()) / "profiles.sqlite"
    file_store = _Store(str(path))
    for profile in store.list():
        file_store.add(profile)
    file_store.close()
    monkeypatch.setenv("AIOS_PROFILES_DB", str(path))
    _Store.reset_default()  # singleton мог жить из другого теста
    return path


def test_cli_cron_plan_generic_lines_for_non_olx(tmp_path, capsys,
                                                 monkeypatch):
    from aios_cli import main
    from aios_core.platforms import ProfileStore as _Store

    profiles_db = tmp_path / "profiles.sqlite"
    store = _Store(str(profiles_db))
    store.add(Profile(platform="instagram", name="main", is_default=True,
                      db_path=str(tmp_path / "ig.sqlite")))
    store.add(Profile(platform="olx", name="work", is_default=True,
                      db_path=str(tmp_path / "olx.sqlite")))
    store.close()
    monkeypatch.setenv("AIOS_PROFILES_DB", str(profiles_db))
    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    _Store.reset_default()  # singleton должен перечитать env этого теста

    main(["cron-plan", "--platform", "instagram"])
    plan = capsys.readouterr().out
    assert "platforms autowatch --platform instagram --profile main" in plan

    # olx остаётся на родной команде (обратная совместимость):
    main(["cron-plan", "--platform", "olx"])
    plan = capsys.readouterr().out
    assert "olx autowatch --profile work" in plan


# ---------------------------------------------------------------------------
# Content categories in CalibrationAdvisor
# ---------------------------------------------------------------------------

def test_calibration_content_categories():
    xml = """<hierarchy>
  <node text="0:32" resource-id="com.demo:id/reel_duration"/>
  <node text="" resource-id="com.demo:id/reel_video_player"/>
  <node text="" resource-id="com.demo:id/story_highlight_cover"/>
  <node text="" resource-id="com.demo:id/adCard">
    <node text="Кросівки Nike Air нові"/>
    <node text="3 200 грн"/>
  </node>
</hierarchy>"""
    hints = CalibrationAdvisor().analyze(xml)
    categories = hints["content_categories"]
    assert hints["card_markers"]  # прежние ключи на месте
    assert categories["video_markers"]
    assert any("reel" in rid for rid in categories["video_markers"])
    assert categories["story_markers"]
    assert categories["duration_labels"] == 1


def test_calibration_content_categories_empty_on_plain_dump():
    hints = CalibrationAdvisor().analyze(
        "<hierarchy><node text='Привіт'/></hierarchy>"
    )
    categories = hints["content_categories"]
    assert categories == {
        "video_markers": [], "story_markers": [], "duration_labels": 0,
    }


# ---------------------------------------------------------------------------
# Guarded messenger REST plane per platform
# ---------------------------------------------------------------------------

@pytest.fixture
async def messenger_client(tmp_path):
    from aios_core.api.app import AIOSAPI
    from aios_core.platforms import load_catalog_file

    load_catalog_file(os.path.join(_PROJECT_ROOT, "platforms", "instagram.yaml"))
    store = ProfileStore(":memory:")
    store.add(Profile(
        platform="instagram", name="main",
        db_path=str(tmp_path / "instagram-main.sqlite"), is_default=True,
    ))
    store.add(Profile(
        platform="instagram", name="second",
        db_path=str(tmp_path / "instagram-second.sqlite"),
    ))
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
        policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
        auth_required=False,
        profile_store=store,
        device_pool=DevicePool(":memory:"),
    )
    app = api.create_starlette_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport,
                           base_url="http://test") as ac:
        yield ac
    store.close()
    descriptor_mod._PLATFORMS.pop("instagram", None)


async def test_rest_module_outbox_guarded_flow(messenger_client):
    send = await messenger_client.post(
        "/api/v1/modules/instagram/outbox/send?profile=main",
        json={"chat_key": "chat:anna", "text": "Добрий день!"},
    )
    assert send.status_code == 200
    payload = send.json()
    assert payload["status"] == "queued"
    assert payload["platform"] == "instagram"

    outbox = await messenger_client.get(
        "/api/v1/modules/instagram/outbox?profile=main",
    )
    entries = outbox.json()["outbox"]
    assert len(entries) == 1
    assert entries[0]["chat_key"] == "chat:anna"
    assert entries[0]["status"] == "pending"

    # flush без устройства — честный failed, без 500:
    flush = await messenger_client.post(
        "/api/v1/modules/instagram/outbox/flush?profile=main", json={},
    )
    flushed = flush.json()["flushed"]
    assert flushed[0]["status"] == "failed"


async def test_rest_module_chats_and_error_paths(messenger_client):
    chats = await messenger_client.get(
        "/api/v1/modules/instagram/chats?profile=main",
    )
    assert chats.status_code == 200
    assert chats.json() == {"platform": "instagram", "threads": []}

    unknown = await messenger_client.get("/api/v1/modules/ghost/chats")
    assert unknown.status_code == 404

    # Профильная изоляция: другой профиль → пустой outbox.
    send = await messenger_client.post(
        "/api/v1/modules/instagram/outbox/send?profile=main",
        json={"chat_key": "c1", "text": "t"},
    )
    assert send.json()["status"] == "queued"
    other = await messenger_client.get(
        "/api/v1/modules/instagram/outbox?profile=second",
    )
    assert other.json()["outbox"] == []
    # А без профиля резолвится реестровый default (main) — запись там:
    default_out = await messenger_client.get(
        "/api/v1/modules/instagram/outbox",
    )
    assert len(default_out.json()["outbox"]) == 1


async def test_rest_module_messenger_module_missing(messenger_client):
    def storage_factory(db_path):
        from aios_core.modules.olx import OLXStorage
        return OLXStorage(db_path)

    def adb_factory(package, serial=None):
        from aios_core.modules.olx.adb import ADBController
        return ADBController(package=package, serial=serial)

    register_platform(PlatformDescriptor(
        name="nomsg", android_package="com.nomsg.app",
        agent_module="no.such.agent", storage_factory=storage_factory,
        adb_factory=adb_factory,
    ))
    try:
        response = await messenger_client.post(
            "/api/v1/modules/nomsg/outbox/send",
            json={"chat_key": "c", "text": "t"},
        )
        assert response.status_code == 404
        assert "no messenger module" in response.json()["error"]
    finally:
        descriptor_mod._PLATFORMS.pop("nomsg", None)
