"""Tests for the H2 batch: calibrate-recipe (on-device hints), ops
dashboard web-pane and the Facebook Marketplace onboarding package.
"""

import json
from pathlib import Path

import pytest
import yaml

from aios_core.platforms import calibration_recipe, dashboard_html
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms import get_platform, load_catalog_file
from aios_core.platforms.recipe import _KIND_HINTS

# ---------------------------------------------------------------------------
# calibration_recipe
# ---------------------------------------------------------------------------


def test_recipe_marketplace_covers_all_surfaces():
    recipe = calibration_recipe("facebook", "com.facebook.katana", kind="marketplace")
    assert recipe["ready"] is False
    assert recipe["missing"] == ["cards", "detail", "messenger", "navigation"]
    calibrate = next(s for s in recipe["steps"] if s["action"] == "calibrate")
    for flag in ("--dump", "--detail", "--messages", "--navigation"):
        assert flag in calibrate["command"]
    assert "platforms/facebook-cards.xml" in calibrate["command"]
    assert recipe["steps"][0]["action"] == "preflight"
    assert "pm path com.facebook.katana" in recipe["steps"][0]["command"]
    assert recipe["steps"][-1]["action"] == "doctor"


def test_recipe_messenger_kind_is_inbox_first():
    recipe = calibration_recipe("whatsapp", "com.whatsapp", kind="messenger")
    # мессенджер-first: только инбокс, без карточной ленты и tab-bar
    assert recipe["missing"] == ["messenger"]
    calibrate = next(s for s in recipe["steps"] if s["action"] == "calibrate")
    assert "--messages" in calibrate["command"]
    assert "--dump" not in calibrate["command"]
    assert "--detail" not in calibrate["command"]
    assert "--navigation" not in calibrate["command"]
    # закрыли инбокс → платформа готова
    done = calibration_recipe(
        "whatsapp",
        "com.whatsapp",
        kind="messenger",
        have_hints={"messenger": {"bubble_markers": [{"resource_id": "x"}]}},
    )
    assert done["ready"] is True
    assert done["missing"] == []


def test_recipe_serial_and_have_hints_skip(tmp_path):
    recipe = calibration_recipe(
        "olx",
        "ua.com.olx",
        kind="marketplace",
        have_hints={
            "cards": {"card_markers": [{"resource_id": "x:id/card"}]},
            "detail": {"seller_markers": [{"resource_id": "x:id/seller"}]},
            "messenger": {"bubble_markers": [{"resource_id": "x:id/row"}]},
            "navigation": {"reels_tab": {"rid_markers": ["x:id/reels"]}},
        },
        serial="emulator-5554",
    )
    assert recipe["ready"] is True
    assert recipe["missing"] == []
    # только preflight + финальный doctor, дампы не нужны
    assert [s["action"] for s in recipe["steps"]] == ["preflight", "doctor"]
    assert "-s emulator-5554 " in recipe["steps"][0]["command"]

    partial = calibration_recipe(
        "olx",
        "ua.com.olx",
        kind="marketplace",
        have_hints={"cards": {"card_markers": [{"resource_id": "x"}]}},
    )
    assert partial["missing"] == ["detail", "messenger", "navigation"]
    calibrate = next(s for s in partial["steps"] if s["action"] == "calibrate")
    assert "--dump" not in calibrate["command"]  # cards уже есть
    assert "--detail" in calibrate["command"]


def test_recipe_unknown_kind_is_honest_error():
    with pytest.raises(ValueError):
        calibration_recipe("x", "y", kind="everything")


def test_recipe_kinds_cover_known_platform_shapes():
    assert _KIND_HINTS["messenger"] == ["messenger"]
    assert _KIND_HINTS["collector"] == ["cards"]
    assert set(_KIND_HINTS["marketplace"]) == {"cards", "detail", "messenger"}


# ---------------------------------------------------------------------------
# platform_doctor --calibrate-recipe wiring
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path, platform, package, hints=None):
    (tmp_path / f"{platform}.yaml").write_text(
        yaml.safe_dump(
            {
                "name": platform,
                "android_package": package,
                "agent_module": f"aios_core.modules.{platform}",
                "storage_class": f"aios_core.modules.{platform}.storage.TestStorage",
                "extras": {"parser_hints": hints or {}},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _hint_markers():
    return {"chat_markers": [{"resource_id": "x:id/row"}]}


def test_doctor_recipe_reports_missing_sections(tmp_path):
    from aios_core.platforms.doctor import platform_doctor

    _write_yaml(tmp_path, "whatsapp", "com.whatsapp")
    report = platform_doctor(
        "whatsapp",
        "com.whatsapp",
        directory=str(tmp_path),
        which=lambda n: "/usr/bin/adb" if n == "adb" else None,
        required_hints=("messenger",),
        report_recipe=True,
    )
    assert "calibrate_recipe" in report
    recipe = report["calibrate_recipe"]
    assert recipe["platform"] == "whatsapp"
    assert recipe["kind"] == "messenger"
    assert recipe["ready"] is False
    assert "messenger" in recipe["missing"]
    assert any(
        "--messages" in s.get("command", "") for s in recipe["steps"] if s["action"] == "calibrate"
    )

    # секция закрыта → рецепт зелёный
    _write_yaml(tmp_path, "whatsapp", "com.whatsapp", {"messenger": _hint_markers()})
    report2 = platform_doctor(
        "whatsapp",
        "com.whatsapp",
        directory=str(tmp_path),
        which=lambda n: "/usr/bin/adb" if n == "adb" else None,
        required_hints=("messenger",),
        report_recipe=True,
    )
    assert report2["calibrate_recipe"]["ready"] is True
    assert "messenger" not in report2["calibrate_recipe"]["missing"]


def test_doctor_without_flag_has_no_recipe(tmp_path):
    from aios_core.platforms.doctor import platform_doctor

    _write_yaml(tmp_path, "whatsapp", "com.whatsapp")
    report = platform_doctor(
        "whatsapp",
        "com.whatsapp",
        directory=str(tmp_path),
        which=lambda n: "/usr/bin/adb" if n == "adb" else None,
        required_hints=("messenger",),
    )
    assert "calibrate_recipe" not in report


def test_cli_platforms_doctor_calibrate_recipe(tmp_path, capsys, monkeypatch):
    from aios_cli import main
    from aios_core.platforms import ProfileStore

    loaded = load_catalog_file(
        str(Path(__file__).resolve().parent.parent / "platforms" / "whatsapp.yaml")
    )
    _write_yaml(tmp_path, "whatsapp", "com.whatsapp")
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    ProfileStore.reset_default()
    main(
        [
            "platforms",
            "doctor",
            "--platform",
            "whatsapp",
            "--directory",
            str(tmp_path),
            "--calibrate-recipe",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert out["calibrate_recipe"]["platform"] == "whatsapp"
    assert out["calibrate_recipe"]["kind"] == "messenger"
    assert out["calibrate_recipe"]["ready"] is False
    for d in loaded:
        descriptor_mod._PLATFORMS.pop(d.name, None)


# ---------------------------------------------------------------------------
# Ops dashboard
# ---------------------------------------------------------------------------


def test_dashboard_html_is_self_contained_and_rwired():
    html = dashboard_html(title="AIOS Ops", api_prefix="/api/v1", refresh_s=5)
    assert html.startswith("<!DOCTYPE html>")
    assert "<style>" in html and "<script>" in html
    for panel in ("panel-stats", "panel-jobs", "panel-devices", "panel-profiles", "panel-shards"):
        assert panel in html
    assert 'const API = "/api/v1";' in html
    assert "5000" in html  # refresh_ms
    # никаких внешних ресурсов: офлайн-просмотр рендерит каркас
    assert "cdn." not in html.lower()
    assert "googleapis" not in html.lower()
    assert "unpkg" not in html.lower()


def test_dashboard_html_custom_prefix_param():
    html = dashboard_html(api_prefix="/v2/api", refresh_s=10)
    assert 'const API = "/v2/api";' in html
    assert "10000" in html


def test_rest_dashboard_page(monkeypatch):
    import os
    import tempfile

    from starlette.testclient import TestClient

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("AIOS_SHARDS_DB", str(Path(tmp) / "shards.sqlite"))
        from aios_core.api.app import AIOSAPI

        api = AIOSAPI(
            db_path=":memory:",
            constitution_dir=os.path.join(root, "docs/constitution"),
            policies_dir=os.path.join(root, "policies"),
            auth_required=False,
        )
        client = TestClient(api.create_starlette_app())
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text
        assert "AIOS Ops" in body
        assert "panel-jobs" in body
        assert "/shards/stats" in body
        # рядом живой REST-plane, на который панель смотрит:
        assert client.get("/api/v1/shards/stats").status_code == 200


# ---------------------------------------------------------------------------
# Fleet telemetry (Prometheus)
# ---------------------------------------------------------------------------


def _telemetry_dbs(tmp_path):
    from aios_core.platforms.devices import DevicePool
    from aios_core.platforms.profile import Profile
    from aios_core.platforms.shardexec import ShardJobs
    from aios_core.platforms.shards import ShardRouter
    from aios_core.platforms.store import ProfileStore

    shards = str(tmp_path / "shards.sqlite")
    profiles = str(tmp_path / "profiles.sqlite")
    devices = str(tmp_path / "devices.sqlite")
    with ShardJobs(shards) as jobs:
        jobs.enqueue("instagram:main", "autopilot")
        jobs.enqueue("olx:work", "reels")
    with DevicePool(devices) as pool:
        pool.register("emulator-5554")
        pool.register("emulator-5556")
        pool.lease("olx:work")
    router = ShardRouter(shards)
    try:
        router.add_host("worker-1", "http://10.0.0.1:8001")
    finally:
        router.close()
    with ProfileStore(profiles) as store:
        store.add(Profile(platform="instagram", name="main"))
        store.add(Profile(platform="olx", name="work"))
    return shards, profiles, devices


def test_fleet_snapshot_and_prometheus_metrics(tmp_path):
    from aios_core.platforms.telemetry import fleet_snapshot, prometheus_metrics

    shards, profiles, devices = _telemetry_dbs(tmp_path)
    snapshot = fleet_snapshot(
        shards_db=shards, profiles_db=profiles, devices_db=devices, catalog_dir="platforms"
    )
    assert snapshot["jobs"]["stats"]["pending"] == 2
    assert snapshot["devices"]["total"] == 2
    assert snapshot["devices"]["leased"] == 1
    assert snapshot["profiles"]["total"] == 2
    assert snapshot["profiles"]["per_platform"] == {"instagram": 1, "olx": 1}
    assert "facebook" in snapshot["platforms"]

    text = prometheus_metrics(
        shards_db=shards, profiles_db=profiles, devices_db=devices, catalog_dir="platforms"
    )
    assert 'aios_shard_jobs{status="pending"} 2' in text
    assert "aios_shard_job_queue_depth 2" in text
    assert "aios_shard_host" in text
    assert 'aios_devices{state="leased"} 1' in text
    assert 'aios_devices{state="registered"} 2' in text
    assert "aios_profiles_total 2" in text
    assert 'aios_profiles{platform="instagram"} 1' in text
    assert "aios_catalog_platforms" in text
    assert text.endswith("\n")


def test_prometheus_metrics_empty_bases_are_honest_zeros(tmp_path):
    from aios_core.platforms.telemetry import prometheus_metrics

    text = prometheus_metrics(
        shards_db=str(tmp_path / "no-shards.sqlite"),
        profiles_db=str(tmp_path / "no-profiles.sqlite"),
        devices_db=str(tmp_path / "no-devices.sqlite"),
        catalog_dir=str(tmp_path),
    )
    assert 'aios_shard_jobs{status="pending"} 0' in text
    assert "aios_profiles_total 0" in text
    assert 'aios_devices{state="registered"} 0' in text
    assert "aios_catalog_platforms 0" in text


def test_rest_metrics_include_fleet_series(tmp_path, monkeypatch):
    import os

    from starlette.testclient import TestClient

    shards, profiles, devices = _telemetry_dbs(tmp_path)
    monkeypatch.setenv("AIOS_SHARDS_DB", shards)
    monkeypatch.setenv("AIOS_PROFILES_DB", profiles)
    monkeypatch.setenv("AIOS_DEVICES_DB", devices)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from aios_core.api.app import AIOSAPI

    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(root, "docs/constitution"),
        policies_dir=os.path.join(root, "policies"),
        auth_required=False,
    )
    client = TestClient(api.create_starlette_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "aios_shard_jobs" in body
    assert 'aios_devices{state="registered"} 2' in body
    assert "aios_profiles_total 2" in body


# ---------------------------------------------------------------------------
# Facebook Marketplace onboarding package
# ---------------------------------------------------------------------------


@pytest.fixture
def facebook_registered():
    loaded = load_catalog_file("platforms/facebook.yaml")
    yield loaded
    for d in loaded:
        descriptor_mod._PLATFORMS.pop(d.name, None)


def test_catalog_facebook_registered(facebook_registered):
    descriptor = get_platform("facebook")
    assert descriptor.android_package == "com.facebook.katana"
    assert descriptor.extras["compliance"]["collector"] is True
    assert descriptor.extras["compliance"]["autopost_allowed"] is False
    storage = descriptor.storage_factory(":memory:")
    storage.close()


def test_facebook_module_classes():
    import importlib

    mod = importlib.import_module("aios_core.modules.facebook")
    for attr in ("FacebookStorage", "FacebookBootstrap", "FacebookMessenger"):
        assert hasattr(mod, attr)
    messenger_cls = mod.FacebookMessenger
    assert messenger_cls.PACKAGE == "com.facebook.katana"
    assert messenger_cls.DEEP_LINK == "fb://messaging"


def test_facebook_messenger_guarded_outbox():
    from aios_core.modules.facebook import FacebookMessenger, FacebookStorage

    chat_xml = (
        '<hierarchy><node class="android.widget.EditText" '
        'resource-id="com.facebook.katana:id/entry" text="" '
        'bounds="[0,2200][900,2300]"/>'
        '<node content-desc="Send" '
        'resource-id="com.facebook.katana:id/send" text="" '
        'bounds="[900,2200][1080,2300]"/></hierarchy>'
    )

    class _ADB:
        package = "com.facebook.katana"

        def __init__(self):
            self.calls = []
            self._dumps = [chat_xml]

        @property
        def adb(self):
            return "adb"

        def run(self, command):
            self.calls.append(command)
            return {"code": 0, "stdout": "", "stderr": ""}

        def dump_ui(self, filename="screen.xml"):
            if not self._dumps:
                return {"code": 1, "stdout": "", "stderr": "no dumps"}
            Path(filename).write_text(self._dumps.pop(0), encoding="utf-8")
            return {"code": 0, "stdout": "", "stderr": ""}

        def tap(self, x, y):
            self.calls.append(("tap", x, y))
            return {"code": 0, "stdout": "", "stderr": ""}

        def input_text(self, text):
            self.calls.append(("input_text", text))
            return {"code": 0, "stdout": "", "stderr": ""}

    storage = FacebookStorage(":memory:")
    hints = {
        "bubble_markers": [{"resource_id": "com.facebook.katana:id/entry"}],
    }
    adb = _ADB()
    messenger = FacebookMessenger(adb=adb, storage=storage, messenger_hints=hints)
    result = messenger.send_reply("chat:anna", "Здравствуйте, актуально!")
    assert result["status"] == "queued"
    assert ("input_text", "Здравствуйте, актуально!") not in adb.calls
    flushed = messenger.flush_outbox()
    assert flushed[0]["status"] == "sent"
    assert ("input_text", "Здравствуйте, актуально!") in adb.calls
    assert any(c == ("tap", 990, 2250) for c in adb.calls if isinstance(c, tuple))
    storage.close()


def test_facebook_bootstrap_doctor(tmp_path):
    from aios_core.modules.facebook import FacebookBootstrap

    class _ADB:
        package = "com.facebook.katana"

        @property
        def adb(self):
            return "adb"

        def run(self, command):
            if "devices" in command:
                return {"code": 0, "stdout": "emulator-5554\tdevice\n", "stderr": ""}
            if "pm path" in command:
                return {"code": 0, "stdout": "package:/data/app/facebook/base.apk", "stderr": ""}
            return {"code": 0, "stdout": "", "stderr": ""}

    _write_yaml(tmp_path, "facebook", "com.facebook.katana")
    report = FacebookBootstrap(
        adb=_ADB(),
        serial="emulator-5554",
        directory=str(tmp_path),
        which=lambda n: "/usr/bin/adb" if n == "adb" else None,
    ).doctor()
    assert report["platform"] == "facebook"
    assert report["checks"]["descriptor"]["ok"] is True
    assert report["checks"]["device"]["ok"] is True
    assert report["checks"]["package"]["ok"] is True
    assert report["checks"]["storage"]["ok"] is True
    assert report["checks"]["hints_cards"]["ok"] is False  # hints пустые
    assert report["checks"]["hints_messenger"]["ok"] is False
    assert report["ok"] is False  # честно: hints ещё не откалиброваны


def test_cli_facebook_dm_guarded(tmp_path, capsys, facebook_registered):
    from aios_cli import main

    db = tmp_path / "fb.sqlite"
    main(["facebook", "dm-send", "--chat", "chat:anna", "--text", "Привет", "--db", str(db)])
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "queued"

    main(["facebook", "dm-outbox", "--db", str(db)])
    outbox = json.loads(capsys.readouterr().out)
    assert len(outbox) == 1
    assert outbox[0]["text"] == "Привет"
