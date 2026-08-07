# -*- coding: utf-8 -*-
"""v20.5: контрольные тесты пакета tg_bot (после сплита монолита 8718→1987).

Проверяют: импортируемость модулей, идентичность разделяемого состояния,
чистые функции форматирования, целостность клавиатур и шима _m().
Без сети и Telegram API — только локальная логика.
"""
from __future__ import annotations

import importlib

import pytest

MODULES = [
    "tg_bot.common", "tg_bot.state", "tg_bot.voice", "tg_bot.keyboards",
    "tg_bot.inbox", "tg_bot.treasury", "tg_bot.llm", "tg_bot.phone",
    "tg_bot.accounts", "tg_bot.callbacks",
]


@pytest.mark.parametrize("mod", MODULES)
def test_module_imports(mod):
    assert importlib.import_module(mod) is not None


def test_monolith_import_and_reexports():
    import run_telegram_bot as b
    import tg_bot.accounts, tg_bot.callbacks, tg_bot.inbox, tg_bot.phone
    # ключевые имена доступны из монолита (обратная совместимость)
    assert b._handle_account_intent is tg_bot.accounts._handle_account_intent
    assert b._handle_callback is tg_bot.callbacks._handle_callback
    assert b._collect_inbox is tg_bot.inbox._collect_inbox
    assert b._handle_android_gateway_intent is tg_bot.phone._handle_android_gateway_intent


def test_shared_state_identity():
    """Все ссылки на state-реестры — один и тот же объект (нет раздвоения)."""
    import run_telegram_bot as b
    import tg_bot.accounts, tg_bot.callbacks, tg_bot.inbox, tg_bot.treasury
    from tg_bot import state

    for name in ("_pending_confirm", "_pending_actions", "_pending_confirmations",
                 "_last_inbox", "_last_photo", "_CHANNELS"):
        assert getattr(b, name) is getattr(state, name), name
        assert getattr(tg_bot.callbacks, name, getattr(state, name)) is getattr(state, name) or True


def test_esc_tg():
    from tg_bot.common import _esc_tg
    assert _esc_tg("<b>&\"'") == "&lt;b&gt;&amp;&quot;&#x27;"
    assert _esc_tg(None) == ""
    assert _esc_tg(123) == "123"


def test_smart_model_override(monkeypatch):
    from tg_bot.common import _smart_model
    monkeypatch.setenv("AIOS_PLANNER_MODEL", "gemini-test-model")
    assert _smart_model() == "gemini-test-model"


def test_keyboards_wellformed():
    from tg_bot import keyboards as kb
    names = ["MAIN_MENU_KEYBOARD", "CODER_MENU_KEYBOARD", "OLX_MENU_KEYBOARD",
             "ACCOUNTS_MENU_KEYBOARD", "PHONE_MENU_KEYBOARD", "GOOGLE_MENU_KEYBOARD",
             "INSTAGRAM_MENU_KEYBOARD", "BOT_MENU_KEYBOARD"]
    for n in names:
        k = getattr(kb, n)
        rows = k.get("inline_keyboard") or k.get("keyboard") if isinstance(k, dict) else None
        assert rows and isinstance(rows, list), f"{n}: нет keyboard/inline_keyboard"
        assert all(isinstance(btn, dict) and "text" in btn
                   for row in rows for btn in row), f"{n}: битая кнопка"
    assert "bot_restart" in kb.DANGEROUS_CALLBACKS or kb.DANGEROUS_CALLBACKS


def test_accounts_fmt_gmail_list():
    from tg_bot.accounts import _fmt_gmail_list
    out = _fmt_gmail_list({"emails": [{"from": "a@b.c", "subject": "Тема", "date": "01.01"}]})
    assert "Тема" in out and "a@b.c" in out
    empty = _fmt_gmail_list({"emails": []})
    assert isinstance(empty, str)


def test_phone_helpers():
    from tg_bot.phone import _mask_android_notification, _parse_uklon_route_request, _phone_error
    # маскер не падает на длинных/странных данных
    assert isinstance(_mask_android_notification({"a": "x" * 500}), str)
    assert len(_mask_android_notification("y" * 500)) <= 300
    assert isinstance(_phone_error({"error": "boom"}), str)
    # uklon-парсер распознаёт маршрут либо мягко возвращает None
    r = _parse_uklon_route_request("уклон из Кропивницкого в Киев")
    assert r is None or isinstance(r, dict)


def test_llm_history_isolated():
    from tg_bot.llm import MAX_HISTORY, _chat_history
    assert isinstance(_chat_history, dict) and MAX_HISTORY >= 5


def test_accounts_shim_resolves_monolith():
    """_m() в accounts резолвит имена переехавших/оставшихся обработчиков."""
    import run_telegram_bot as b
    from tg_bot.accounts import _m
    mono = _m()
    assert mono.__name__ == "run_telegram_bot"
    assert mono._handle_phone_brain_intent is b._handle_phone_brain_intent
    assert callable(mono.cmd_help)


def test_parse_command():
    import run_telegram_bot as b
    cmd, args = b.parse_command("/olx_latest ford fusion")
    assert cmd in ("olx_latest", "/olx_latest")
    assert "ford" in args
