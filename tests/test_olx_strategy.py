"""Tests for OLX profile management, competitor surveillance, strategy
advisor and the fresh-server bootstrap/doctor tooling."""

import json
from datetime import datetime, timezone

import pytest

from aios_core.modules.olx import (
    ACTION_EDIT_PRICE,
    ACTION_KEEP,
    ACTION_REPOST,
    AdCard,
    CompetitiveWatch,
    OLXBootstrap,
    OLXStorage,
    OwnAd,
    ProfileEditor,
    ProfileParser,
    StrategyAdvisor,
    derive_query,
    title_similarity,
)

NOW = datetime(2026, 7, 21, 15, 0, 0, tzinfo=timezone.utc)

PROFILE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="Ім'я: Олександр"/>
  <node text="Телефон: +380671234567"/>
  <node text="E-mail: user@example.com"/>
  <node text="Місто: Дніпро"/>
  <node text="Про себе: Продаж автозапчастин"/>
  <node text="На OLX з: квіт. 2021"/>
  <node text="Push-сповіщення: увімкнено"/>
  <node text="Email-розсилка: вимкнено"/>
</hierarchy>
"""


# --- Profile & settings --------------------------------------------------------


def test_profile_parser_extracts_fields_and_settings():
    parser = ProfileParser()
    profile = parser.parse_profile(PROFILE_XML)

    assert profile.fields["name"] == "Олександр"
    assert profile.fields["phone"] == "+380671234567"
    assert profile.fields["city"] == "Дніпро"
    assert profile.fields["member_since"] == "квіт. 2021"

    texts = parser._texts(PROFILE_XML)
    settings = parser.settings_from_texts(texts)
    assert settings.toggles["push_notifications"] is True
    assert settings.toggles["email_digest"] is False


def test_profile_editor_dry_run_and_confirm():
    storage = OLXStorage()
    editor = ProfileEditor()

    dry = editor.apply(storage, "name", "Нове Ім'я")
    assert dry["status"] == "dry_run"
    assert dry["executed"] is False
    stored = storage.profile_all()
    assert stored["_pending_name"]["value"] == "Нове Ім'я"
    assert "name" not in stored

    done = editor.apply(storage, "name", "Нове Ім'я", confirm=True)
    assert done["status"] == "executed"
    stored = storage.profile_all()
    assert stored["name"]["value"] == "Нове Ім'я"
    assert stored["_pending_name"]["value"] is None
    assert len(dry["steps"]) >= 4
    storage.close()


# --- Competitor surveillance ------------------------------------------------------


def test_derive_query_and_similarity():
    assert derive_query("Лобове скло BMW X3 G01") == "лобове скло"
    assert title_similarity("Лобове скло BMW", "скло лобове оригінал") > 0.5
    assert title_similarity("Лобове скло", "Коврики салона") == 0.0


def _market():
    return [
        AdCard(title="Лобове скло оригінал", price=6800.0, currency="UAH",
               city="Київ", query="q"),
        AdCard(title="Скло лобове Mercedes", price=5500.0, currency="UAH",
               city="Львів", query="q"),
        AdCard(title="Коврики гумові салона", price=300.0, currency="UAH",
               city="Одеса", query="q"),
    ]


def test_competitive_refresh_links_similar_ads():
    storage = OLXStorage()
    for card in _market():
        storage.save_ads([card])
    own = OwnAd(title="Лобове скло BMW X3", price=7000.0, currency="UAH")

    watch = CompetitiveWatch(storage)
    result = watch.refresh([own])

    assert result["total_links"] == 2  # коврики не схожі
    assert result["new_links"] == 2
    assert result["per_own"][own.fingerprint]["cheaper_competitors"] == 2

    # Idempotent: refresh again — no new links.
    again = watch.refresh([own])
    assert again["new_links"] == 0

    report = watch.report(own.fingerprint)
    assert report["competitors_count"] == 2
    assert report["cheapest_price"] == 5500.0
    assert report["competitors"][0]["ad"]["price"] in (5500.0, 6800.0)

    position = watch.price_position(own)
    assert position["cheaper_competitors"] == 2
    assert position["rank"] == 3
    assert position["median_competitor_price"] == 6150.0
    storage.close()


# --- Strategy advisor ----------------------------------------------------------


def _storage_with_portfolio():
    storage = OLXStorage()
    # Undercut own ad: two cheaper similar competitors.
    storage.upsert_own_ad(
        OwnAd(title="Лобове оголошення", price=9000.0, currency="UAH", views=40,
              url="https://www.olx.ua/d/uk/obyavlenie/a-IDaaa1a.html"),
        seen_at="2026-07-19T10:00:00+00:00",
    )
    # Old stagnant own ad.
    storage.upsert_own_ad(
        OwnAd(title="Багажник на дах", price=1000.0, currency="UAH", views=2,
              url="https://www.olx.ua/d/uk/obyavlenie/b-IDbbb1b.html"),
        seen_at="2026-07-01T10:00:00+00:00",
    )
    for card in [
        AdCard(title="Лобове оголошення схоже", price=7000.0, currency="UAH",
               city="Київ", query="q"),
        AdCard(title="Аналог лобове оголошення", price=6500.0, currency="UAH",
               city="Львів", query="q"),
    ]:
        storage.save_ads([card])
    return storage


def test_advisor_actions_priorities():
    storage = _storage_with_portfolio()
    advisor = StrategyAdvisor(storage, undercut_alert=2)
    advice = advisor.advise_actions(now=NOW)

    by_action = {item.action: item for item in advice}
    assert ACTION_EDIT_PRICE in by_action
    edit = by_action[ACTION_EDIT_PRICE]
    assert edit.priority == 1
    assert edit.suggested_price < 9000.0
    assert "конкурент" in edit.reason

    assert ACTION_REPOST in by_action
    assert by_action[ACTION_REPOST].priority == 2
    storage.close()


def test_advisor_new_listings_fills_gaps():
    storage = _storage_with_portfolio()
    # An active niche the portfolio does not cover.
    for index in range(6):
        storage.save_ads([AdCard(
            title=f"Велосипед BMX модель {index}", price=4000.0 + index * 100,
            currency="UAH", city="Дніпро", query="bmx велосипед",
        )])

    advisor = StrategyAdvisor(storage)
    new_listings = advisor.advise_new_listings()

    assert new_listings, "uncovered active niche must be suggested"
    first = new_listings[0]
    assert first.query == "bmx велосипед"
    assert first.active_competitors == 6
    assert first.suggested_price is not None
    assert first.reason and "ніша" in first.reason
    # A query whose tokens are covered by the portfolio is not suggested:
    covered = AdCard(title="Лобове оголошення схоже", price=7000.0,
                     currency="UAH", query="лобове оголошення")
    storage.save_ads([covered])
    fresh = advisor.advise_new_listings()
    assert all(item.query != "лобове оголошення" for item in fresh)
    storage.close()


# --- Bootstrap & doctor ---------------------------------------------------------


def test_bootstrap_plan_contains_emulator_pipeline():
    bootstrap = OLXBootstrap(project_root="/repo")
    steps = bootstrap.plan(emulator=True, apt=True, olx_apk="/tmp/olx.apk")
    names = [step.name for step in steps]
    assert names == [
        "apt-packages", "python-deps", "platform-tools", "adbkeyboard-apk",
        "sdk-cmdline-tools", "sdk-packages", "create-avd", "start-emulator",
        "device-setup", "verify",
    ]
    flat = bootstrap.print_plan(emulator=True, apt=True, olx_apk="/tmp/olx.apk")
    assert "platform-tools-latest-linux.zip" in flat
    assert "system-images;android-34" in flat
    assert "avdmanager create avd" in flat
    assert "adb install -r /tmp/olx.apk" in flat
    assert "ime set com.android.adbkeyboard/.AdbIME" in flat


def test_bootstrap_execute_aborts_on_failure():
    calls = []

    def failing_runner(command):
        calls.append(command)
        return {"code": 1, "stdout": "", "stderr": "boom"}

    bootstrap = OLXBootstrap(runner=failing_runner, project_root="/repo")
    results = bootstrap.execute(emulator=False, apt=True)
    assert results[-1]["aborted"] is True
    assert calls and "apt-get update" in calls[0]


def _emulated_runner(command):
    if command == "adb version":
        return {"code": 0, "stdout": "Android Debug Bridge version 1.0.41", "stderr": ""}
    if command == "adb devices":
        return {"code": 0, "stdout": "List of devices attached\nemulator-5554\tdevice", "stderr": ""}
    if "pm list packages" in command:
        return {"code": 0, "stdout": "package:ua.slando", "stderr": ""}
    if "default_input_method" in command:
        return {"code": 0, "stdout": "com.android.adbkeyboard/.AdbIME", "stderr": ""}
    return {"code": 0, "stdout": "", "stderr": ""}


def test_doctor_ready_in_emulator_and_hints_when_bare():
    ready = OLXBootstrap(runner=_emulated_runner).doctor_report()
    assert ready["ready"] is True
    by_name = {check["name"]: check for check in ready["checks"]}
    assert by_name["adb_installed"]["ok"] is True
    assert by_name["device_online"]["ok"] is True
    assert by_name["olx_installed"]["ok"] is True
    assert by_name["adbkeyboard_ime"]["ok"] is True

    bare = OLXBootstrap(runner=lambda cmd: {"code": 127, "stdout": "", "stderr": "not found"}).doctor_report()
    assert bare["ready"] is False
    adb_check = next(c for c in bare["checks"] if c["name"] == "adb_installed")
    assert adb_check["ok"] is False
    assert "platform-tools" in adb_check["hint"]
