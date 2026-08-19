"""Tests: одна кнопка «Трейдинг» + allowlist с дополнительным чатом."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tg_bot.keyboards import MAIN_MENU_INLINE, MAIN_MENU_KEYBOARD  # noqa: E402


def test_main_menu_has_only_trading_button():
    rows = MAIN_MENU_KEYBOARD["keyboard"]
    texts = [btn["text"] for row in rows for btn in row]
    assert texts == ["📈 Трейдинг"], texts


def test_main_menu_inline_has_only_trading():
    rows = MAIN_MENU_INLINE["inline_keyboard"]
    datas = [btn["callback_data"] for row in rows for btn in row]
    assert datas == ["nav_trading"], datas
    texts = [btn["text"] for row in rows for btn in row]
    assert texts == ["📈 Трейдинг"], texts


def test_extra_chat_ids_allowed(monkeypatch):
    import run_telegram_bot as bot

    def fake_cred(name):
        if name == "telegram_owner_chat_id":
            return "588113957"
        if name == "telegram_extra_chat_ids":
            return "839699134,123456789"
        return ""

    monkeypatch.setattr(bot, "os", bot.os)  # no-op для ясности
    monkeypatch.setattr("tg_bot.credentials.read_systemd_credential", fake_cred)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    allowed = bot._allowed_chat_ids()
    assert 588113957 in allowed
    assert 839699134 in allowed
    assert 123456789 in allowed


def test_extra_chat_ids_absent_is_safe(monkeypatch):
    import run_telegram_bot as bot

    def fake_cred(name):
        return "588113957" if name == "telegram_owner_chat_id" else ""

    monkeypatch.setattr("tg_bot.credentials.read_systemd_credential", fake_cred)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    allowed = bot._allowed_chat_ids()
    assert allowed == {588113957}


def test_sender_accepts_chat_argument():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "send_trading_report.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--chat"' in src
    assert "TARGET_CHAT = args.chat" in src
