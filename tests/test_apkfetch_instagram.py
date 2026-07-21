"""Tests for ApkFetch, secrets, detail/messenger calibration, marker drift,
pool-aware bootup and the Instagram onboarding (login-drive)."""

import json
import sys
from pathlib import Path

import pytest

from aios_core.platforms import (
    DetailCalibrationAdvisor,
    DevicePool,
    bootup_platform,
    check_platform_markers,
    diff_markers,
    fetch_apk,
    load_secrets_file,
    merge_hints,
    required_secret,
    resolve_apk,
    scaffold_platform,
    secret,
    write_hints_to_descriptor,
)
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms.calibrate import CalibrationAdvisor
from aios_core.platforms.secrets import env_name

DUMP_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.demo:id/adCard">
    <node text="Продам велосипед у гарному стані" resource-id=""/>
    <node text="4 500 грн" resource-id=""/>
    <node text="Київ" resource-id=""/>
  </node>
  <node text="" resource-id="com.demo:id/adCard">
    <node text="iPhone 12 128GB" resource-id=""/>
    <node text="12 000 грн" resource-id=""/>
    <node text="Дніпро" resource-id=""/>
  </node>
</hierarchy>
"""

# Те же карточки, но верстку переименовали (обновление приложения):
DRIFTED_DUMP_XML = DUMP_XML.replace("adCard", "listingTile")

DETAIL_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="Велосипед горний" resource-id="com.demo:id/detailTitle"/>
  <node text="8 500 грн" resource-id="com.demo:id/detailPrice"/>
  <node text="" resource-id="com.demo:id/sellerAvatar"/>
  <node text="Продавець Оксана" resource-id="com.demo:id/userName"/>
  <node text="Написати" resource-id="com.demo:id/messageButton"/>
  <node text="Продається чудовий велосипед, майже новий, торг можливий."
        resource-id="com.demo:id/descriptionText"/>
</hierarchy>
"""

MESSENGER_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node resource-id="com.demo:id/messagesList" text="">
    <node text="Привіт!" resource-id="com.demo:id/messageBubble"/>
    <node text="Ще актуально?" resource-id="com.demo:id/messageBubble"/>
  </node>
  <node class="android.widget.EditText" resource-id="com.demo:id/inputField" text=""/>
  <node content-desc="Send" resource-id="com.demo:id/sendButton" text=""/>
</hierarchy>
"""

CARD_HINTS = CalibrationAdvisor().analyze(DUMP_XML)


def _badging(apk_path, package="com.boot.two"):
    return {
        "code": 0,
        "stdout": (
            f"package: name='{package}'\n"
            "application-label:'Boot Two'\n"
            f"launchable-activity: name='{package}.MainActivity'\n"
            "targetSdkVersion:'34'\n"
        ),
        "stderr": "",
    }


def _fake_apkeep(package, out_dir, source="apkpure"):
    Path(out_dir, f"{package}.apk").write_text("fake-apk", encoding="utf-8")
    return {"code": 0, "stdout": f"downloaded {package}", "stderr": ""}


def _importable(tmp_path, *names):
    import aios_core.modules as modules_pkg

    extra = str(tmp_path / "aios_core" / "modules")
    if extra not in modules_pkg.__path__:
        modules_pkg.__path__.append(extra)
    for name in names:
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.{name}{suffix}", None)
    return modules_pkg, extra


def _cleanup(tmp_path, extra, modules_pkg, platform, module):
    descriptor_mod._PLATFORMS.pop(platform, None)
    modules_pkg.__path__.remove(extra)
    for suffix in ("", ".card_parser", ".storage"):
        sys.modules.pop(f"aios_core.modules.{module}{suffix}", None)


# ---------------------------------------------------------------------------
# ApkFetch
# ---------------------------------------------------------------------------

def test_fetch_apk_success(tmp_path):
    path = fetch_apk("com.demo.app", out_dir=tmp_path, runner=_fake_apkeep)
    assert path.endswith("com.demo.app.apk")
    assert Path(path).exists()


def test_fetch_apk_failure_and_no_file(tmp_path):
    def failing(package, out_dir, source="apkpure"):
        return {"code": 1, "stdout": "", "stderr": "network error"}

    with pytest.raises(ValueError, match="apkeep failed"):
        fetch_apk("com.x", out_dir=tmp_path, runner=failing)

    def silent(package, out_dir, source="apkpure"):
        return {"code": 0, "stdout": "done", "stderr": ""}

    with pytest.raises(ValueError, match="no .apk appeared"):
        fetch_apk("com.x", out_dir=tmp_path, runner=silent)


def test_resolve_apk_passthrough_cache_and_fetch(tmp_path):
    real = tmp_path / "demo.apk"
    real.write_text("bytes", encoding="utf-8")
    assert resolve_apk(str(real)) == str(real)
    with pytest.raises(ValueError, match="apk not found"):
        resolve_apk(str(tmp_path / "nope.apk"))

    cached_dir = tmp_path / "cache"
    cached_dir.mkdir()
    (cached_dir / "com.demo.app.apk").write_text("old", encoding="utf-8")
    assert resolve_apk("com.demo.app", out_dir=cached_dir).endswith(
        "com.demo.app.apk"
    )

    with pytest.raises(ValueError, match="--fetch"):
        resolve_apk("com.other.app", out_dir=cached_dir)

    fetched = resolve_apk(
        "com.other.app", out_dir=cached_dir, fetch=True,
        runner=_fake_apkeep,
    )
    assert Path(fetched).exists()


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------

def test_secret_env_precedence(monkeypatch):
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "plat-user")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__WORK__USERNAME", "prof-user")
    assert secret("instagram", "USERNAME") == "plat-user"
    assert secret("instagram", "USERNAME", profile="work") == "prof-user"
    assert secret("instagram", "PASSWORD") is None
    assert secret("instagram", "PASSWORD", default="fallback") == "fallback"
    assert env_name("instagram", "PASSWORD", profile="work") == \
        "AIOS_SECRET__INSTAGRAM__WORK__PASSWORD"


def test_required_secret_errors_with_env_name(monkeypatch):
    monkeypatch.delenv("AIOS_SECRET__INSTAGRAM__PASSWORD", raising=False)
    with pytest.raises(ValueError, match="AIOS_SECRET__INSTAGRAM__PASSWORD"):
        required_secret("instagram", "PASSWORD")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__PASSWORD", "s3cret")
    assert required_secret("instagram", "PASSWORD") == "s3cret"


def test_load_secrets_file_no_override_by_default(tmp_path, monkeypatch):
    secrets_file = tmp_path / "secrets.env"
    secrets_file.write_text(
        "# comment\n"
        "AIOS_SECRET__INSTAGRAM__USERNAME='file-user'\n"
        "AIOS_SECRET__INSTAGRAM__PASSWORD=file-pass\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "env-user")
    applied = load_secrets_file(str(secrets_file))
    assert applied == 1  # USERNAME уже в env — не затирается
    assert secret("instagram", "USERNAME") == "env-user"
    assert secret("instagram", "PASSWORD") == "file-pass"

    applied = load_secrets_file(str(secrets_file), override=True)
    assert applied == 2
    assert secret("instagram", "USERNAME") == "file-user"
    assert load_secrets_file(str(tmp_path / "absent.env")) == 0


# ---------------------------------------------------------------------------
# Detail/messenger calibration
# ---------------------------------------------------------------------------

def test_detail_advisor_finds_price_seller_cta():
    hints = DetailCalibrationAdvisor().analyze_detail(DETAIL_XML)
    price_ids = [p["resource_id"] for p in hints["price_nodes"]]
    assert "com.demo:id/detailprice" in price_ids
    assert "com.demo:id/selleravatar" in hints["seller_markers"]
    assert "com.demo:id/username" in hints["seller_markers"]
    assert hints["cta_markers"][0]["resource_id"] == \
        "com.demo:id/messagebutton"
    assert hints["description_nodes"] == 1
    assert "найдены" in hints["hint"]


def test_detail_advisor_empty_screen_hint():
    hints = DetailCalibrationAdvisor().analyze_detail(
        "<hierarchy><node text='' resource-id=''/></hierarchy>"
    )
    assert hints["price_nodes"] == []
    assert "не распознан" in hints["hint"]


def test_messenger_advisor_finds_input_send_bubbles():
    hints = DetailCalibrationAdvisor().analyze_messenger(MESSENGER_XML)
    assert "android.widget.EditText" in hints["input_classes"]
    assert hints["send_markers"][0]["resource_id"] == \
        "com.demo:id/sendbutton"
    assert hints["bubble_markers"][0]["resource_id"] == \
        "com.demo:id/messagebubble"
    assert hints["bubble_markers"][0]["occurrences"] == 2


def test_merge_hints_combines_sections():
    detail = DetailCalibrationAdvisor().analyze_detail(DETAIL_XML)
    messenger = DetailCalibrationAdvisor().analyze_messenger(MESSENGER_XML)
    merged = merge_hints(CARD_HINTS, detail, messenger)
    assert merged["card_markers"]          # карточки сохранены
    assert merged["detail"]["seller_markers"]
    assert merged["messenger"]["send_markers"]
    # Без опциональных секций — структура прежняя:
    assert "detail" not in merge_hints(CARD_HINTS)


# ---------------------------------------------------------------------------
# Marker drift
# ---------------------------------------------------------------------------

def test_diff_markers_added_removed_kept():
    old = {"card_markers": [{"resource_id": "com.x:id/adCard"}]}
    new = {"card_markers": [{"resource_id": "com.x:id/listingTile"}]}
    diff = diff_markers(old, new)
    assert diff["removed"] == ["adcard"]
    assert diff["added"] == ["listingtile"]
    assert diff["kept"] == []

    same = diff_markers(old, old)
    assert same == {"removed": [], "added": [], "kept": ["adcard"]}


def test_check_platform_markers_ok_drift_no_baseline(tmp_path):
    scaffold_platform("mrk", "com.mrk.app", project_root=tmp_path)
    # no-baseline:
    report = check_platform_markers(
        "mrk", DUMP_XML, directory=tmp_path / "platforms",
    )
    assert report["status"] == "no-baseline"

    write_hints_to_descriptor(
        "mrk", CARD_HINTS, directory=tmp_path / "platforms",
    )
    report = check_platform_markers(
        "mrk", DUMP_XML, directory=tmp_path / "platforms",
    )
    assert report["status"] == "ok"
    assert report["diff"]["kept"] == ["adcard"]

    report = check_platform_markers(
        "mrk", DRIFTED_DUMP_XML, directory=tmp_path / "platforms",
    )
    assert report["status"] == "drift"
    assert report["diff"]["removed"] == ["adcard"]
    assert "recalibrate" in report["hint"]

    with pytest.raises(ValueError, match="descriptor not found"):
        check_platform_markers(
            "ghost", DUMP_XML, directory=tmp_path / "platforms",
        )


# ---------------------------------------------------------------------------
# Bootup: fetch + pool/serial
# ---------------------------------------------------------------------------

def test_bootup_fetch_apk_then_pipeline(tmp_path):
    dump = tmp_path / "dump.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")
    modules_pkg, extra = _importable(tmp_path, "two")
    try:
        report = bootup_platform(
            apk_path="com.boot.two", fetch=True,
            apks_dir=tmp_path / "apks",
            apk_runner=_fake_apkeep, runner=_badging,
            dump_path=str(dump), project_root=tmp_path,
        )
        try:
            assert report["status"] == "ready"
            assert report["platform"] == "two"
            apk_step = report["steps"]["apk"]
            assert apk_step["fetched"] is True
            assert (tmp_path / "apks" / "com.boot.two.apk").exists()
            assert report["steps"]["verify"]["cards"] == 2
        finally:
            descriptor_mod._PLATFORMS.pop("two", None)
    finally:
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.two{suffix}", None)
        modules_pkg.__path__.remove(extra)


def test_bootup_fetch_missing_apk_without_flag_errors(tmp_path):
    with pytest.raises(ValueError, match="--fetch"):
        bootup_platform(
            apk_path="com.offline.app", project_root=tmp_path,
            apks_dir=tmp_path / "apks", dry_run=False,
        )


def test_bootup_injected_aapt_runner_allows_stub_apk(tmp_path):
    """Stub-путь APK + инъецированный aapt-runner: файла не требуется."""
    modules_pkg, extra = _importable(tmp_path, "two")
    try:
        report = bootup_platform(
            apk_path="stub.apk", project_root=tmp_path, runner=_badging,
            driver=lambda package, query, serial=None: DUMP_XML,
        )
        try:
            assert report["steps"]["apk"]["mode"] == "stub"
            assert report["status"] == "ready"
        finally:
            descriptor_mod._PLATFORMS.pop("two", None)
    finally:
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.two{suffix}", None)
        modules_pkg.__path__.remove(extra)


def test_bootup_pool_lease_drive_release(tmp_path):
    pool = DevicePool(":memory:")
    pool.register("emulator-1", avd_name="avd1")
    calls = []

    def driver(package, query, serial=None):
        calls.append({"package": package, "serial": serial})
        return DUMP_XML

    modules_pkg, extra = _importable(tmp_path, "pooldemo")
    try:
        report = bootup_platform(
            name="pooldemo", package="com.pool.demo",
            project_root=tmp_path, pool=pool, driver=driver,
        )
        try:
            assert report["status"] == "ready"
            calibrate = report["steps"]["calibrate"]
            assert calibrate["leased_serial"] == "emulator-1"
            assert calibrate["lease_key"] == "pooldemo:calibration"
            assert calibrate["released"] is True
            # Устройство вернулось в idle:
            assert pool.get("emulator-1")["status"] == "idle"
        finally:
            descriptor_mod._PLATFORMS.pop("pooldemo", None)
    finally:
        pool.close()
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.pooldemo{suffix}", None)
        modules_pkg.__path__.remove(extra)
    assert calls == [{"package": "com.pool.demo", "serial": "emulator-1"}]


def test_bootup_pool_empty_skips_calibrate(tmp_path):
    pool = DevicePool(":memory:")  # устройств нет

    def driver(package, query, serial=None):
        raise AssertionError("driver must not be called without a device")

    modules_pkg, extra = _importable(tmp_path, "nodev2")
    try:
        report = bootup_platform(
            name="nodev2", package="com.nodev2.app",
            project_root=tmp_path, pool=pool, driver=driver,
        )
        try:
            assert report["status"] == "scaffolded"
            assert "no free device" in \
                report["steps"]["calibrate"]["reason"]
        finally:
            descriptor_mod._PLATFORMS.pop("nodev2", None)
    finally:
        pool.close()
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.nodev2{suffix}", None)
        modules_pkg.__path__.remove(extra)


def test_bootup_explicit_serial_passthrough(tmp_path):
    calls = []

    def driver(package, query, serial=None):
        calls.append(serial)
        return DUMP_XML

    modules_pkg, extra = _importable(tmp_path, "serialo")
    try:
        report = bootup_platform(
            name="serialo", package="com.serialo.app",
            project_root=tmp_path, serial="emulator-9", driver=driver,
        )
        try:
            assert "leased_serial" not in report["steps"]["calibrate"]
        finally:
            descriptor_mod._PLATFORMS.pop("serialo", None)
    finally:
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.serialo{suffix}", None)
        modules_pkg.__path__.remove(extra)
    assert calls == ["emulator-9"]


# ---------------------------------------------------------------------------
# Instagram login-drive
# ---------------------------------------------------------------------------

LOGIN_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node resource-id="com.instagram.android:id/login_button" text="Log in"/>
  <node resource-id="com.instagram.android:id/create_button" text="Create new account"/>
</hierarchy>
"""

IG_FEED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node resource-id="com.instagram.android:id/row_feed_photo" text="Photo by shop"/>
  <node resource-id="com.instagram.android:id/row_feed_photo" text="Price post"/>
</hierarchy>
"""


class _FakeADB:
    """ADBController-заглушка с очередью дампов."""

    def __init__(self, dumps):
        self.dumps = list(dumps)
        self.calls = []

    @property
    def adb(self):
        return "adb"

    def open_app(self):
        self.calls.append("open_app")
        return {"code": 0, "stdout": "", "stderr": ""}

    def run(self, command):
        self.calls.append(command)
        return {"code": 0, "stdout": "", "stderr": ""}

    def input_text(self, text):
        self.calls.append(("input_text", text))
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename):
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}


def test_login_screen_detected():
    from aios_core.modules.instagram import login_screen_detected

    assert login_screen_detected(LOGIN_XML)
    assert not login_screen_detected(IG_FEED_XML)
    assert not login_screen_detected("")


def test_instagram_drive_logs_in_and_returns_feed(monkeypatch):
    from aios_core.modules.instagram import InstagramLoginDriver

    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "u@example.com")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__PASSWORD", "p@ss")
    adb = _FakeADB([LOGIN_XML, IG_FEED_XML])
    driver = InstagramLoginDriver(adb=adb, open_wait_s=0, login_wait_s=0)
    xml = driver.drive("com.instagram.android", query="sneakers")
    assert xml == IG_FEED_XML
    inputs = [c for c in adb.calls if isinstance(c, tuple)]
    assert inputs == [("input_text", "u@example.com"),
                      ("input_text", "p@ss")]
    assert any("keyevent 61" in c for c in adb.calls
               if isinstance(c, str))  # TAB между полями
    assert any("keyevent 66" in c for c in adb.calls
               if isinstance(c, str))  # ENTER — отправка формы


def test_instagram_drive_without_credentials_explains_env(monkeypatch):
    from aios_core.modules.instagram import InstagramLoginDriver

    monkeypatch.delenv("AIOS_SECRET__INSTAGRAM__USERNAME", raising=False)
    adb = _FakeADB([LOGIN_XML])
    driver = InstagramLoginDriver(adb=adb, open_wait_s=0, login_wait_s=0)
    with pytest.raises(ValueError, match="AIOS_SECRET__INSTAGRAM__USERNAME"):
        driver.drive("com.instagram.android")


def test_instagram_drive_login_wall_stuck_is_honest(monkeypatch):
    from aios_core.modules.instagram import InstagramLoginDriver

    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "u")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__PASSWORD", "p")
    adb = _FakeADB([LOGIN_XML, LOGIN_XML])  # логин не прошёл
    driver = InstagramLoginDriver(adb=adb, open_wait_s=0, login_wait_s=0)
    with pytest.raises(ValueError, match="did not pass the login wall"):
        driver.drive("com.instagram.android")


def test_instagram_drive_already_logged_in_skips_flow():
    from aios_core.modules.instagram import InstagramLoginDriver

    adb = _FakeADB([IG_FEED_XML])
    driver = InstagramLoginDriver(adb=adb, open_wait_s=0, login_wait_s=0)
    xml = driver.drive("com.instagram.android")
    assert xml == IG_FEED_XML
    assert not [c for c in adb.calls if isinstance(c, tuple)]  # без ввода


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_platforms_fetch_apk(monkeypatch, capsys, tmp_path):
    from aios_cli import main
    import aios_core.platforms as platforms_mod

    def fake_fetch(package, out_dir="apks", source="apkpure", runner=None):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        target = Path(out_dir, f"{package}.apk")
        target.write_text("apk", encoding="utf-8")
        return str(target)

    monkeypatch.setattr(platforms_mod, "fetch_apk", fake_fetch)
    main(["platforms", "fetch-apk", "com.instagram.android",
          "--out", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["package"] == "com.instagram.android"
    assert Path(out["apk"]).exists()

    def failing(package, out_dir="apks", source="apkpure", runner=None):
        raise ValueError("apkeep failed (install: cargo install apkeep)")

    monkeypatch.setattr(platforms_mod, "fetch_apk", failing)
    main(["platforms", "fetch-apk", "com.x", "--out", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert "apkeep failed" in out["error"]


def test_cli_platforms_bootup_fetch_end_to_end(tmp_path, capsys,
                                               monkeypatch):
    from aios_cli import main
    from aios_core.platforms import apkfetch as apkfetch_mod
    from aios_core.platforms import scaffold as scaffold_mod

    dump = tmp_path / "dump.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")
    monkeypatch.setattr(apkfetch_mod, "_apkeep", _fake_apkeep)
    monkeypatch.setattr(
        scaffold_mod, "_badging",
        lambda apk: _badging(apk, package="com.clie2e.app"),
    )
    modules_pkg, extra = _importable(tmp_path, "clie2e")
    try:
        main(["platforms", "bootup",
              "--apk", "com.clie2e.app", "--name", "clie2e", "--fetch",
              "--apks-dir", str(tmp_path / "apks"),
              "--dump", str(dump), "--root", str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        try:
            assert out["status"] == "ready"
            assert out["steps"]["apk"]["fetched"] is True
            assert out["steps"]["verify"]["cards"] == 2
        finally:
            descriptor_mod._PLATFORMS.pop("clie2e", None)
    finally:
        for suffix in ("", ".card_parser", ".storage"):
            sys.modules.pop(f"aios_core.modules.clie2e{suffix}", None)
        modules_pkg.__path__.remove(extra)

    # Без --fetch — чистая JSON-ошибка про apkeep/--fetch.
    monkeypatch.setattr(
        apkfetch_mod, "_apkeep",
        lambda *a, **k: {"code": 1, "stdout": "", "stderr": "no apkeep"},
    )
    main(["platforms", "bootup",
          "--apk", "com.clie2e.app", "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert "--fetch" in out["error"]


def test_cli_platforms_calibrate_merge_and_marker_check(
    tmp_path, capsys, monkeypatch,
):
    from aios_cli import main

    scaffold_platform("climrg", "com.climrg.app", project_root=tmp_path)
    feed = tmp_path / "feed.xml"
    detail = tmp_path / "detail.xml"
    messages = tmp_path / "messages.xml"
    feed.write_text(DUMP_XML, encoding="utf-8")
    detail.write_text(DETAIL_XML, encoding="utf-8")
    messages.write_text(MESSENGER_XML, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    main(["platforms", "calibrate", "--platform", "climrg",
          "--dump", str(feed), "--detail", str(detail),
          "--messages", str(messages), "--write"])
    out = json.loads(capsys.readouterr().out)
    assert out["hints"]["card_markers"]
    assert out["hints"]["detail"]["seller_markers"]
    assert out["hints"]["messenger"]["send_markers"]
    assert out["written"].endswith("climrg.yaml")

    # marker-check: тот же дамп — ok.
    main(["platforms", "marker-check", "--platform", "climrg",
          "--dump", str(feed)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"

    # верстка переименована — drift.
    drifted = tmp_path / "drifted.xml"
    drifted.write_text(DRIFTED_DUMP_XML, encoding="utf-8")
    main(["platforms", "marker-check", "--platform", "climrg",
          "--dump", str(drifted)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "drift"
    assert out["diff"]["removed"] == ["adcard"]
