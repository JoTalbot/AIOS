"""Tests for the full Instagram functionality and hints-runtime adapters:

HintDetailParser/HintSender/chat parser markers, PointDrive search,
InstagramCollector/DetailParser/Messenger (guarded outbox), Bootstrap
doctor, CLI instagram group, cron-plan marker-check lines."""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

from aios_core.platforms import (
    HintDetailParser,
    HintSender,
    PointDrive,
    load_hints_section,
    write_hints_to_descriptor,
)
from aios_core.platforms.calibrate import CalibrationAdvisor, DetailCalibrationAdvisor
from aios_core.platforms.runtime_hints import chat_list_parser_for, detail_parser_for

FEED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Кросівки Nike Air нові" resource-id=""/>
    <node text="3 200 грн" resource-id=""/>
    <node text="Київ" resource-id=""/>
  </node>
  <node text="" resource-id="com.instagram.android:id/shop_card">
    <node text="Сумка шкіряна ручна робота" resource-id=""/>
    <node text="1 850 грн" resource-id=""/>
    <node text="Львів" resource-id=""/>
  </node>
</hierarchy>
"""

EMPTY_FEED_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"

DETAIL_HINTS = DetailCalibrationAdvisor().analyze_detail(
    """<hierarchy>
  <node text="Кросівки Nike Air" resource-id="com.instagram.android:id/postTitle"/>
  <node text="3 200 грн" resource-id="com.instagram.android:id/postPrice"/>
  <node text="shop_sneakers_kyiv" resource-id="com.instagram.android:id/userName"/>
  <node text="Написати" resource-id="com.instagram.android:id/messageButton"/>
  <node text="Оригінальні кросівки, повний комплект, чек, доставка НП."
        resource-id="com.instagram.android:id/captionText"/>
</hierarchy>"""
)

DETAIL_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="Кросівки Nike Air" resource-id="com.instagram.android:id/postTitle"/>
  <node text="3 200 грн" resource-id="com.instagram.android:id/postPrice"/>
  <node text="shop_sneakers_kyiv" resource-id="com.instagram.android:id/userName"/>
  <node text="Написати" resource-id="com.instagram.android:id/messageButton"/>
  <node text="Оригінальні кросівки, повний комплект, чек, доставка НП."
        resource-id="com.instagram.android:id/captionText"/>
</hierarchy>
"""

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

INBOX_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="com.instagram.android:id/messageBubble"
        bounds="[0,100][1080,240]">
    <node text="buyer_anna" resource-id=""/>
    <node text="Добрий день, ще актуально?" resource-id=""/>
    <node text="14:32" resource-id=""/>
    <node text="2" resource-id=""/>
  </node>
</hierarchy>
"""

# Секция messenger из калибровки диалога + маркеры строк инбокса:
MESSENGER_HINTS = {
    **DetailCalibrationAdvisor().analyze_messenger(CHAT_XML),
    "bubble_markers": [
        {"resource_id": "com.instagram.android:id/messageBubble", "occurrences": 3},
    ],
}


class _ADB:
    """Универсальный fake-ADB: дампы по очереди + записанные вызовы."""

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
        if "devices" in command:
            return {"code": 0, "stdout": "emulator-5554\tdevice", "stderr": ""}
        return {"code": 0, "stdout": "", "stderr": ""}

    def open_app(self):
        self.calls.append("open_app")
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename):
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


def _write_instagram_yaml(tmp_path, hints=None):
    doc = {
        "name": "instagram",
        "android_package": "com.instagram.android",
        "extras": {"parser_hints": hints or {}},
    }
    path = tmp_path / "instagram.yaml"
    (tmp_path / "instagram.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8"
    )
    return path


# ---------------------------------------------------------------------------
# HintDetailParser / load_hints_section
# ---------------------------------------------------------------------------


def test_hint_detail_parser_fields():
    parser = HintDetailParser(DETAIL_HINTS)
    assert parser.configured
    result = parser.parse(DETAIL_XML)
    assert result["price"] == 3200.0
    assert result["currency"] == "UAH"
    assert result["seller"] == "shop_sneakers_kyiv"
    assert result["title"] == "Кросівки Nike Air"
    assert result["description"].startswith("Оригінальні кросівки")
    assert result["cta_texts"] == ["Написати"]
    assert result["texts_seen"] == 5


def test_hint_detail_parser_unconfigured_shape_mode():
    parser = HintDetailParser({})
    assert not parser.configured
    result = parser.parse(DETAIL_XML)
    assert result["price"] == 3200.0  # цена — по форме текста
    assert result["title"] == "Кросівки Nike Air"
    assert result["seller"] is None  # маркеров нет


def test_load_hints_section_and_parsers_for(tmp_path):
    _write_instagram_yaml(
        tmp_path,
        {
            "detail": DETAIL_HINTS,
            "messenger": MESSENGER_HINTS,
        },
    )
    assert load_hints_section("instagram", "detail", tmp_path)["cta_markers"]
    assert load_hints_section("instagram", "keys-missing", tmp_path) == {}
    with pytest.raises(ValueError, match="descriptor not found"):
        load_hints_section("ghost", "detail", tmp_path)

    detail_parser = detail_parser_for("instagram", tmp_path)
    assert detail_parser.configured
    assert detail_parser.parse(DETAIL_XML)["seller"] == "shop_sneakers_kyiv"

    chat_parser = chat_list_parser_for("instagram", tmp_path)
    threads = chat_parser.parse(INBOX_XML)
    assert len(threads) == 1
    assert threads[0].interlocutor == "buyer_anna"
    assert threads[0].unread_count == 2
    assert "актуально" in threads[0].snippet


# ---------------------------------------------------------------------------
# HintSender / PointDrive
# ---------------------------------------------------------------------------


def test_hint_sender_taps_input_types_and_taps_send():
    adb = _ADB()
    sender = HintSender(adb, MESSENGER_HINTS)
    result = sender.type_and_send("Добрий день!", CHAT_XML)
    assert result["code"] == 0
    actions = [step["action"] for step in result["steps"]]
    assert actions == ["tap_input", "input_text", "tap_send"]
    # Центр EditText bounds [0,2200][900,2300] и кнопки [900,2200][1080,2300]:
    assert ("tap", 450, 2250) in adb.calls
    assert ("tap", 990, 2250) in adb.calls
    assert ("input_text", "Добрий день!") in adb.calls


def test_hint_sender_enter_fallback_without_send_marker():
    # Узла кнопки отправки нет совсем — только поле ввода:
    xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node class="android.widget.EditText"
        resource-id="com.instagram.android:id/row_thread_composer_edittext"
        text="" bounds="[0,2200][900,2300]"/>
</hierarchy>
"""
    adb = _ADB()
    result = HintSender(adb, {}).type_and_send("hi", xml)
    actions = [step["action"] for step in result["steps"]]
    assert "keyevent_enter" in actions
    assert "tap_send" not in actions


def test_hint_sender_dumps_screen_itself_when_no_xml():
    adb = _ADB([CHAT_XML])
    result = HintSender(adb, MESSENGER_HINTS).type_and_send("як справи?")
    assert result["code"] == 0
    assert any(isinstance(c, tuple) and c[0] == "input_text" for c in adb.calls)


def test_pointdrive_finds_search_and_runs_query():
    search_xml = (
        "<hierarchy>"
        '<node class="android.widget.EditText" '
        'resource-id="com.instagram.android:id/action_bar_search_edit_text" '
        'text="" bounds="[0,50][800,150]"/>'
        "</hierarchy>"
    )
    adb = _ADB([search_xml, FEED_XML])
    drive = PointDrive(adb, open_wait_s=0, search_wait_s=0)
    xml = drive.drive("com.instagram.android", "кросівки")
    assert xml == FEED_XML
    assert ("tap", 400, 100) in adb.calls
    assert ("input_text", "кросівки") in adb.calls
    assert any("keyevent 66" in c for c in adb.calls if isinstance(c, str))


def test_pointdrive_no_search_input_returns_feed_as_is():
    adb = _ADB([FEED_XML])
    drive = PointDrive(adb, open_wait_s=0)
    assert drive.drive("com.instagram.android", "q?") == FEED_XML
    assert not [c for c in adb.calls if isinstance(c, tuple) and c[0] == "tap"]


def test_pointdrive_open_app_failure_is_honest():
    class BrokenADB(_ADB):
        def open_app(self):
            return {"code": 1, "stdout": "", "stderr": "no device"}

    with pytest.raises(ValueError, match="open_app failed"):
        PointDrive(BrokenADB(), open_wait_s=0).drive("com.x")


# ---------------------------------------------------------------------------
# InstagramCollector / login+search chaining
# ---------------------------------------------------------------------------


def test_instagram_collector_with_driver_and_storage(tmp_path):
    calls = []

    def driver(package, query):
        calls.append({"package": package, "query": query})

    adb = _ADB([FEED_XML, EMPTY_FEED_XML, EMPTY_FEED_XML])
    card_hints = CalibrationAdvisor().analyze(FEED_XML)
    _write_instagram_yaml(tmp_path, card_hints)

    from aios_core.modules.instagram import InstagramCollector, InstagramStorage

    collector = InstagramCollector(adb=adb, driver=driver, directory=str(tmp_path))
    cards = collector.collect(query="кросівки")
    assert len(cards) == 2
    assert cards[0].title == "Кросівки Nike Air нові"
    assert cards[0].price == 3200.0
    assert calls == [{"package": "com.instagram.android", "query": "кросівки"}]

    # Вновь — с записью в хранилище:
    adb2 = _ADB([FEED_XML, EMPTY_FEED_XML, EMPTY_FEED_XML])
    collector = InstagramCollector(adb=adb2, directory=str(tmp_path))
    storage = InstagramStorage(str(tmp_path / "ig.sqlite"))
    summary = collector.collect_to_storage(storage, query="кросівки")
    assert summary == {"parsed": 2, "inserted": 2, "deactivated": 0}
    assert len(storage.get_ads()) == 2
    storage.close()


def test_instagram_collector_parser_override_and_missing_hints(tmp_path):
    from aios_core.modules.instagram import InstagramCollector
    from aios_core.platforms import build_parser

    # Явный парсер имеет приоритет над дескриптором:
    explicit = build_parser(CalibrationAdvisor().analyze(FEED_XML))
    collector = InstagramCollector(
        adb=_ADB([FEED_XML]), parser=explicit, directory=str(tmp_path)
    )  # yaml отсутствует
    assert collector.resolve_parser() is explicit

    # Без парсера и без дескриптора — честная подсказка:
    collector = InstagramCollector(adb=_ADB(), directory=str(tmp_path))
    with pytest.raises(ValueError, match="bootup"):
        collector.resolve_parser()


def test_instagram_login_drive_chains_search_when_query(monkeypatch):
    from aios_core.modules.instagram import InstagramLoginDriver

    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "u")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__PASSWORD", "p")
    login_xml = (
        "<hierarchy><node "
        'resource-id="com.instagram.android:id/login_button" '
        'text="Log in"/></hierarchy>'
    )
    search_calls = []

    class FakeSearch:
        def search_in_open_app(self, query, xml=None):
            search_calls.append({"query": query, "xml_after_login": xml})
            return FEED_XML

    adb = _ADB([login_xml, "<hierarchy/>"])  # login wall → post-login dump
    driver = InstagramLoginDriver(adb=adb, open_wait_s=0, login_wait_s=0, search_drive=FakeSearch())
    xml = driver.drive("com.instagram.android", query="кросівки")
    assert xml == FEED_XML
    assert search_calls[0]["query"] == "кросівки"


# ---------------------------------------------------------------------------
# InstagramDetailParser / InstagramMessenger / Bootstrap
# ---------------------------------------------------------------------------


def test_instagram_detail_parser_from_descriptor(tmp_path):
    from aios_core.modules.instagram import InstagramDetailParser

    _write_instagram_yaml(tmp_path, {"detail": DETAIL_HINTS})
    parser = InstagramDetailParser(directory=str(tmp_path))
    assert parser.configured
    assert parser.parse(DETAIL_XML)["cta_texts"] == ["Написати"]


def test_instagram_messenger_guarded_outbox_flow(tmp_path):
    from aios_core.modules.instagram import InstagramMessenger, InstagramStorage

    _write_instagram_yaml(tmp_path, {"messenger": MESSENGER_HINTS})
    adb = _ADB([CHAT_XML])  # один дамп для executor-этапа
    storage = InstagramStorage(str(tmp_path / "ig.sqlite"))
    messenger = InstagramMessenger(adb=adb, storage=storage, directory=str(tmp_path))

    # По умолчанию — только очередь, устройство не трогается:
    result = messenger.send_reply("chat:anna", "Ще актуально")
    assert result["status"] == "queued"
    assert adb.calls == []

    pending = storage.outbox_pending()
    assert len(pending) == 1 and pending[0]["text"] == "Ще актуально"

    # Одобренная отправка проходит device-executor:
    flushed = messenger.flush_outbox()
    assert flushed == [{"id": pending[0]["id"], "status": "sent"}]
    inputs = [c for c in adb.calls if isinstance(c, tuple) and c[0] == "input_text"]
    assert inputs == [("input_text", "Ще актуально")]
    assert storage.outbox_list("sent")
    storage.close()


def test_instagram_messenger_auto_send_and_open_chats(tmp_path):
    from aios_core.modules.instagram import InstagramMessenger, InstagramStorage

    adb = _ADB([CHAT_XML], adb_prefix="adb -s emulator-5557")
    storage = InstagramStorage(":memory:")
    messenger = InstagramMessenger(adb=adb, storage=storage, messenger_hints=MESSENGER_HINTS)
    result = messenger.send_reply("chat:x", " Ціна актуальна ", auto_send=True)
    assert result["status"] == "sent"
    assert result["adb"]["code"] == 0
    # open_chats — deep link Direct inbox с serial-префиксом:
    messenger.open_chats()
    assert any(
        "direct/inbox" in c and "adb -s emulator-5557" in c for c in adb.calls if isinstance(c, str)
    )
    storage.close()


def test_instagram_messenger_list_chats_uses_hints(tmp_path):
    from aios_core.modules.instagram import InstagramMessenger

    adb = _ADB([INBOX_XML])
    messenger = InstagramMessenger(adb=adb, storage=None, messenger_hints=MESSENGER_HINTS)
    threads = messenger.list_chats()
    assert len(threads) == 1
    assert threads[0].interlocutor == "buyer_anna"
    assert threads[0].tap_center == (540, 170)


def test_instagram_bootstrap_doctor_report(tmp_path, monkeypatch):
    from aios_core.modules.instagram import InstagramBootstrap

    _write_instagram_yaml(
        tmp_path,
        {
            "card_markers": [{"resource_id": "com.instagram.android:id/shop_card"}],
            "detail": DETAIL_HINTS,
        },
    )
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "user-secret-value")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__PASSWORD", "pass-secret-value")
    bootstrap = InstagramBootstrap(
        adb=_ADB(),
        serial="emulator-5554",
        directory=str(tmp_path),
        which=lambda name: "/usr/bin/adb" if name == "adb" else None,
    )
    report = bootstrap.doctor()
    assert report["ok"] is True
    assert report["checks"]["secrets_password"]["ok"] is True
    # Значения секретов не светятся в отчёте:
    assert "user-secret-value" not in json.dumps(report)
    assert "pass-secret-value" not in json.dumps(report)
    assert report["checks"]["card_markers"]["ok"] is True
    assert report["checks"]["device"]["ok"] is True


def test_instagram_bootstrap_missing_pieces(tmp_path, monkeypatch):
    from aios_core.modules.instagram import InstagramBootstrap

    monkeypatch.delenv("AIOS_SECRET__INSTAGRAM__USERNAME", raising=False)
    monkeypatch.delenv("AIOS_SECRET__INSTAGRAM__PASSWORD", raising=False)
    bootstrap = InstagramBootstrap(
        directory=str(tmp_path),
        which=lambda name: None,
    )
    report = bootstrap.doctor()
    assert report["ok"] is False
    assert report["checks"]["adb_binary"]["ok"] is False
    assert "AIOS_SECRET__INSTAGRAM__PASSWORD" in report["checks"]["secrets_password"]["detail"]
    assert report["checks"]["descriptor"]["ok"] is False


# ---------------------------------------------------------------------------
# CLI instagram group + cron-plan marker lines
# ---------------------------------------------------------------------------


def test_cli_instagram_doctor_json(monkeypatch, capsys):
    from aios_cli import main

    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__USERNAME", "u@x.com")
    monkeypatch.setenv("AIOS_SECRET__INSTAGRAM__PASSWORD", "p")
    main(["instagram", "doctor"])
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == "instagram"
    assert out["checks"]["secrets_username"]["ok"] is True
    assert "checks" in out and "adb_binary" in out["checks"]


def test_cli_instagram_dm_guarded_flow(tmp_path, capsys):
    from aios_cli import main

    db = str(tmp_path / "ig.sqlite")
    main(["instagram", "dm-send", "--chat", "chat:anna", "--text", "Добрий день!", "--db", db])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "queued"
    assert out["outbox_id"] >= 1

    main(["instagram", "dm-outbox", "--db", db])
    entries = json.loads(capsys.readouterr().out)
    assert len(entries) == 1 and entries[0]["chat_key"] == "chat:anna"
    assert entries[0]["status"] == "pending"

    # flush без устройства — честный failed, без traceback:
    main(["instagram", "dm-flush", "--db", db])
    flushed = json.loads(capsys.readouterr().out)["flushed"]
    assert flushed[0]["status"] == "failed"


def test_cli_instagram_login_drive_with_fakes(tmp_path, capsys, monkeypatch):
    from aios_cli import main
    from aios_core.modules import instagram as ig_mod

    _write_instagram_yaml(tmp_path, CalibrationAdvisor().analyze(FEED_XML))

    class FakeLoginDriver:
        def __init__(self, adb=None, search_drive=None):
            pass

        def drive(self, package, query=None):
            return FEED_XML

    monkeypatch.setattr(ig_mod, "InstagramLoginDriver", FakeLoginDriver)
    main(["instagram", "login-drive", "--query", "кросівки", "--directory", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["login_wall"] is False
    assert out["cards"][0]["title"] == "Кросівки Nike Air нові"
    assert out["cards"][0]["price"] == 3200.0


def test_cli_cron_plan_includes_marker_check_lines(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    monkeypatch.chdir(_repo_root())
    main(["cron-plan", "--with-marker-check"])
    plan = capsys.readouterr().out
    assert "platforms marker-check" in plan
    assert "--platform olx" in plan and "--platform instagram" in plan
    assert "marker-olx.xml" in plan
    # Строки закомментированы — безопасный шаблон:
    for line in plan.splitlines():
        if "marker-check" in line and "--platform" in line:
            assert line.startswith("#")


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
