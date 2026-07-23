"""Tests for the mega-batch: onboarding wizard, WhatsApp/Viber generic
messengers, TikTok onboarding package, generic reels/doctor CLI and
pull-first cron plans + shard jobs REST plane.
"""

import json
from pathlib import Path

import pytest
import yaml

from aios_core.platforms import (
    ShardJobs,
    ShardRouter,
    get_platform,
    load_catalog_file,
)
from aios_core.platforms import descriptor as descriptor_mod

CHAT_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node class="android.widget.EditText" resource-id="com.whatsapp:id/entry"
        text="" bounds="[0,2200][900,2300]"/>
  <node content-desc="Send" resource-id="com.whatsapp:id/send"
        text="" bounds="[900,2200][1080,2300]"/>
</hierarchy>
"""

INBOX_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.whatsapp:id/row_chat"
        bounds="[0,100][1080,240]">
    <node text="buyer_anna" resource-id=""/>
    <node text="Добрий день, актуально?" resource-id=""/>
  </node>
</hierarchy>
"""

EMPTY_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"


class _ADB:
    package = "com.whatsapp"

    def __init__(self, dumps=(), devices=""):
        self.dumps = list(dumps)
        self.calls = []
        self._devices = devices

    @property
    def adb(self):
        return "adb"

    def run(self, command):
        self.calls.append(command)
        if "devices" in command:
            return {"code": 0, "stdout": self._devices, "stderr": ""}
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename="screen.xml"):
        if not self.dumps:
            return {"code": 1, "stdout": "", "stderr": "no dumps"}
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}

    def tap(self, x, y):
        self.calls.append(("tap", x, y))
        return {"code": 0, "stdout": "", "stderr": ""}

    def swipe(self, *a, **k):
        return {"code": 0, "stdout": "", "stderr": ""}

    def input_text(self, text):
        self.calls.append(("input_text", text))
        return {"code": 0, "stdout": "", "stderr": ""}


@pytest.fixture
def modules_path(tmp_path):
    """Чини́т импорт tmp-scaffolded модулей (aios_core.modules.__path__)."""
    import aios_core.modules as modules_pkg

    extra = str(tmp_path / "aios_core" / "modules")
    (tmp_path / "aios_core" / "modules").mkdir(parents=True, exist_ok=True)
    modules_pkg.__path__.append(extra)
    yield extra
    modules_pkg.__path__.remove(extra)


MESSENGER_HINTS = {
    "chat_markers": [{"resource_id": "com.whatsapp:id/row_chat"}],
    "bubble_markers": [{"resource_id": "com.whatsapp:id/row_chat"}],
}


def _write_yaml(tmp_path, platform, package, hints=None):
    (tmp_path / f"{platform}.yaml").write_text(
        yaml.safe_dump(
            {
                "name": platform,
                "android_package": package,
                "agent_module": f"aios_core.modules.{platform}",
                "storage_class": f"aios_core.modules.{platform}.storage.{platform.capitalize()}Storage",
                "extras": {
                    "parser_hints": hints or {},
                    "compliance": {
                        "autopost_allowed": False,
                        "messenger": "approval-only",
                        "collector": True,
                    },
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


@pytest.fixture
def registered():
    platforms = []
    for name in ("whatsapp", "viber", "tiktok"):
        for loaded in load_catalog_file(f"platforms/{name}.yaml"):
            platforms.append(loaded)
    yield platforms
    for d in platforms:
        descriptor_mod._PLATFORMS.pop(d.name, None)


# ---------------------------------------------------------------------------
# Catalog onboarding packages (whatsapp/viber/tiktok)
# ---------------------------------------------------------------------------


def test_new_platforms_registered_from_catalog(registered):
    for name, package in (
        ("whatsapp", "com.whatsapp"),
        ("viber", "com.viber.voip"),
        ("tiktok", "com.zhiliaoapp.musically"),
    ):
        d = get_platform(name)
        assert d.android_package == package
        storage = d.storage_factory(":memory:")
        storage.close()
        assert d.extras["compliance"]["autopost_allowed"] is False


def test_modules_import_and_classes():
    import importlib

    brands = {"whatsapp": "WhatsApp", "viber": "Viber", "tiktok": "TikTok"}
    for name in ("whatsapp", "viber", "tiktok"):
        mod = importlib.import_module(f"aios_core.modules.{name}")
        camel = brands[name]
        assert hasattr(mod, f"{camel}Storage")
        assert hasattr(mod, f"{camel}Bootstrap")
        assert hasattr(mod, f"{camel}Messenger")


# ---------------------------------------------------------------------------
# HintsMessenger (whatsapp instance)
# ---------------------------------------------------------------------------


def test_hints_messenger_guarded_outbox_and_flush(tmp_path):
    from aios_core.modules.whatsapp import WhatsAppMessenger, WhatsAppStorage

    storage = WhatsAppStorage(":memory:")
    adb = _ADB([CHAT_XML])
    messenger = WhatsAppMessenger(adb=adb, storage=storage, messenger_hints=MESSENGER_HINTS)
    # guarded: без auto_send — молча в очередь, устройство не тронуто:
    result = messenger.send_reply("chat:anna", "Добрий день!")
    assert result["status"] == "queued"
    assert ("input_text", "Добрий день!") not in adb.calls

    flushed = messenger.flush_outbox()
    assert flushed[0]["status"] == "sent"
    assert ("input_text", "Добрий день!") in adb.calls
    assert any(c == ("tap", 990, 2250) for c in adb.calls if isinstance(c, tuple))
    assert storage.outbox_list(status="pending") == []
    storage.close()


def test_hints_messenger_open_chats_deeplink_and_list(tmp_path):
    from aios_core.modules.whatsapp import WhatsAppMessenger

    adb = _ADB([INBOX_XML])
    messenger = WhatsAppMessenger(adb=adb, storage=None, messenger_hints=MESSENGER_HINTS)
    result = messenger.open_chats()
    assert result["code"] == 0
    assert any("whatsapp://" in c for c in adb.calls if isinstance(c, str))
    threads = messenger.list_chats()
    assert len(threads) == 1 and threads[0].interlocutor == "buyer_anna"


def test_hints_messenger_uncalibrated_is_honest_empty():
    from aios_core.modules.viber import ViberMessenger

    messenger = ViberMessenger(adb=_ADB([INBOX_XML]), storage=None, messenger_hints={})
    assert messenger.list_chats() == []  # честно: маркеры не откалиброваны
    result = messenger.open_chats()
    assert result["code"] == 0  # viber://chats deep link


def test_bootstrap_doctor_reports_gaps(tmp_path, monkeypatch):
    from aios_core.modules.whatsapp import WhatsAppBootstrap

    monkeypatch.delenv("AIOS_SECRET__WHATSAPP__USERNAME", raising=False)
    report = WhatsAppBootstrap(
        adb=_ADB(devices="emulator-5554\tdevice\n"),
        serial="emulator-5554",
        directory=str(tmp_path),
        which=lambda n: "/usr/bin/adb" if n == "adb" else None,
    ).doctor()
    assert report["platform"] == "whatsapp"
    assert report["checks"]["adb_binary"]["ok"] is True
    assert report["checks"]["device"]["ok"] is True
    assert report["checks"]["descriptor"]["ok"] is False  # tmp без yaml
    assert report["checks"]["storage"]["ok"] is True

    _write_yaml(tmp_path, "whatsapp", "com.whatsapp", {"messenger": MESSENGER_HINTS})
    report2 = WhatsAppBootstrap(directory=str(tmp_path)).doctor()
    assert report2["checks"]["descriptor"]["ok"] is True
    assert report2["checks"]["hints_messenger"]["ok"] is True


# ---------------------------------------------------------------------------
# Onboarding wizard
# ---------------------------------------------------------------------------


def test_onboard_wizard_ready_report(tmp_path, monkeypatch, modules_path):
    from aios_core.platforms.onboard import onboard_package

    feed = tmp_path / "feed.xml"
    feed.write_text(
        "<hierarchy><node text='' resource-id='com.demo:id/adCard'>"
        "<node text='Велосипед' resource-id=''/><node text='3 200 грн' "
        "resource-id=''/></node></hierarchy>",
        encoding="utf-8",
    )
    calls = []

    def driver(package, query=None, serial=None):
        calls.append(serial)
        return feed.read_text(encoding="utf-8")

    report = onboard_package(
        apk=None,
        name="wizzdemo",
        package="com.wizz.demo",
        project_root=str(tmp_path),
        driver=driver,
        serial="emulator-5554",
        dry_run=False,
    )
    assert report["platform"] == "wizzdemo"
    assert report["status"] == "ready"
    assert report["passport"]["verified_cards"] >= 1
    assert calls == ["emulator-5554"]
    assert any("autowatch" in c for c in report["next_commands"])
    descriptor_mod._PLATFORMS.pop("wizzdemo", None)


def test_onboard_wizard_needs_device_honest(tmp_path, modules_path):
    from aios_core.platforms.onboard import onboard_package

    report = onboard_package(
        apk=None,
        name="wizzneeds",
        package="com.wizz.needs",
        project_root=str(tmp_path),
        dry_run=False,
    )
    assert report["status"] != "ready"
    assert any("калибровка" in c or "--dump" in c for c in report["next_commands"])
    descriptor_mod._PLATFORMS.pop("wizzneeds", None)


def test_cli_onboard_dry_run(tmp_path, capsys):
    from aios_cli import main

    main(
        [
            "onboard",
            "--name",
            "wizzcli",
            "--package",
            "com.wizz.cli",
            "--root",
            str(tmp_path),
            "--no-fetch",
            "--dry-run",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert out["status"] in ("planned", "scaffolded", "calibration-empty")
    assert out["platform"] == "wizzcli"
    descriptor_mod._PLATFORMS.pop("wizzcli", None)


# ---------------------------------------------------------------------------
# Generic platforms reels/doctor CLI (tiktok)
# ---------------------------------------------------------------------------


def _reels_xml(*titles):
    nodes = "\n".join(
        '  <node text="" resource-id="com.zhiliaoapp.musically:id/reel_card">\n'
        f'    <node text="{title}" resource-id=""/>\n'
        '    <node text="0:15" resource-id=""/>\n'
        "  </node>"
        for title in titles
    )
    return f"<hierarchy>\n{nodes}\n</hierarchy>"


def test_cli_platforms_reels_tiktok(tmp_path, capsys, monkeypatch, registered):
    from aios_cli import main
    from aios_core.modules.olx import adb as adb_mod

    fake = _ADB([_reels_xml("TT1", "TT2"), EMPTY_XML])
    monkeypatch.setattr(adb_mod, "ADBController", lambda *a, **k: fake)
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    from aios_core.platforms import ProfileStore

    ProfileStore.reset_default()
    _write_yaml(tmp_path, "tiktok", "com.zhiliaoapp.musically")
    db = tmp_path / "tt.sqlite"
    main(
        [
            "platforms",
            "reels",
            "--platform",
            "tiktok",
            "--db",
            str(db),
            "--max",
            "10",
            "--directory",
            str(tmp_path),
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == "tiktok"
    assert out["new"] == 2 and out["cards"][0]["title"] == "TT1"


def test_cli_platforms_doctor_tiktok(tmp_path, capsys, monkeypatch, registered):
    from aios_cli import main

    _write_yaml(tmp_path, "tiktok", "com.zhiliaoapp.musically")
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    from aios_core.platforms import ProfileStore

    ProfileStore.reset_default()
    main(["platforms", "doctor", "--platform", "tiktok", "--directory", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == "tiktok"
    assert out["checks"]["descriptor"]["ok"] is True


def test_cli_whatsapp_dm_guarded(tmp_path, capsys, registered):
    from aios_cli import main

    db = tmp_path / "wa.sqlite"
    main(["whatsapp", "dm-send", "--chat", "chat:anna", "--text", "Добрий день!", "--db", str(db)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "queued"
    main(["whatsapp", "dm-outbox", "--db", str(db)])
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1 and rows[0]["status"] == "pending"


# ---------------------------------------------------------------------------
# Pull-first cron-plan + jobs REST plane
# ---------------------------------------------------------------------------


def test_cron_plan_via_shards_enqueues(tmp_path, capsys, monkeypatch):
    from aios_cli import main
    from aios_core.platforms import Profile, ProfileStore

    profiles_db = tmp_path / "profiles.sqlite"
    store = ProfileStore(str(profiles_db))
    store.add(
        Profile(
            platform="instagram", name="main", is_default=True, db_path=str(tmp_path / "ig.sqlite")
        )
    )
    store.add(
        Profile(platform="tiktok", name="fun", is_default=True, db_path=str(tmp_path / "tt.sqlite"))
    )
    store.close()
    monkeypatch.setenv("AIOS_PROFILES_DB", str(profiles_db))
    ProfileStore.reset_default()
    main(["cron-plan", "--platform", "instagram", "--via-shards"])
    plan = capsys.readouterr().out
    assert "shards enqueue --profile instagram:main --kind autopilot" in plan
    main(["cron-plan", "--platform", "tiktok", "--via-shards"])
    plan = capsys.readouterr().out
    assert "нет builtin job kind для tiktok" in plan


def test_rest_shard_jobs_plane(monkeypatch):
    from starlette.testclient import TestClient

    import os
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("AIOS_SHARDS_DB", str(Path(tmp) / "shards.sqlite"))
        monkeypatch.setenv("AIOS_PROFILES_DB", str(Path(tmp) / "profiles.sqlite"))
        monkeypatch.setenv("AIOS_DEVICES_DB", str(Path(tmp) / "devices.sqlite"))
        router = ShardRouter(str(Path(tmp) / "shards.sqlite"))
        router.add_host("worker-1", "http://10.0.0.1:8001")
        router.route_for("instagram:main")
        router.close()
        from aios_core.api.app import AIOSAPI

        api = AIOSAPI(
            db_path=":memory:",
            constitution_dir=os.path.join(root, "docs/constitution"),
            policies_dir=os.path.join(root, "policies"),
            auth_required=False,
        )
        client = TestClient(api.create_starlette_app())

        response = client.post(
            "/api/v1/shards/jobs",
            json={
                "profile": "instagram:main",
                "kind": "autopilot",
                "payload": {"args": ["--max", "3"]},
            },
        )
        assert response.status_code == 201
        assert response.json()["enqueued"] >= 1

        response = client.post("/api/v1/shards/jobs", json={"profile": "x:y"})
        assert response.status_code == 400

        response = client.get("/api/v1/shards/jobs?status=pending")
        jobs = response.json()["jobs"]
        assert jobs and jobs[0]["kind"] == "autopilot"

        response = client.get("/api/v1/shards/stats")
        stats = response.json()
        assert stats["pending"] == 1 and stats["queue_depth"] == 1
