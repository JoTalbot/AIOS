"""Тесты модуля напоминаний tg_bot/reminders.py (выделен из монолита)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tg_bot import reminders as rem


class FakeAPI:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, **kw):
        self.messages.append(text)


def test_load_reminders_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(rem, "REMINDERS_FILE", tmp_path / "reminders.json")
    assert rem._load_reminders() == []


def test_save_load_reminders_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(rem, "REMINDERS_FILE", tmp_path / "reminders.json")
    items = [{"chat_id": 1, "at": "2026-08-09T10:00:00", "text": "позвонить"}]
    rem._save_reminders(items)
    assert rem._load_reminders() == items


def test_handle_reminder_time(monkeypatch):
    api = FakeAPI()
    monkeypatch.setattr(rem, "REMINDERS_FILE", Path("/tmp/rem_test.json"))
    # убрать остатки
    Path("/tmp/rem_test.json").unlink(missing_ok=True)
    rem._handle_reminder(api, 1, "напомни завтра в 15:00 позвонить Мише")
    assert any("Напомню" in x for x in api.messages)
    items = rem._load_reminders()
    assert items and items[0]["text"] == "позвонить Мише"


def test_handle_reminder_through(monkeypatch):
    api = FakeAPI()
    monkeypatch.setattr(rem, "REMINDERS_FILE", Path("/tmp/rem_test2.json"))
    Path("/tmp/rem_test2.json").unlink(missing_ok=True)
    rem._handle_reminder(api, 1, "напомни через 30 минут выпить воды")
    assert any("через 30" in x for x in api.messages)
    items = rem._load_reminders()
    assert items and items[0]["text"] == "выпить воды"


def test_handle_reminder_repeat(monkeypatch):
    api = FakeAPI()
    monkeypatch.setattr(rem, "REMINDERS_FILE", Path("/tmp/rem_test3.json"))
    Path("/tmp/rem_test3.json").unlink(missing_ok=True)
    rem._handle_reminder(api, 1, "напоминай каждый день в 09:00 чистить зубы")
    assert any("Напоминаю день" in x for x in api.messages)
    items = rem._load_reminders()
    assert items and items[0]["repeat"] == "день"


def test_handle_reminder_bad_format(monkeypatch):
    api = FakeAPI()
    monkeypatch.setattr(rem, "REMINDERS_FILE", Path("/tmp/rem_test4.json"))
    rem._handle_reminder(api, 1, "напомни что-то без времени")
    assert any("Формат" in x for x in api.messages)


def test_templates_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(rem, "TEMPLATES_FILE", tmp_path / "templates.json")
    rem._save_templates({"greet": "Привет!"})
    assert rem._load_templates() == {"greet": "Привет!"}
