"""Tests: кнопка «Трейдинг» (текст) ведёт на человеческий отчёт."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tg_bot.trading_report import send_full_report  # noqa: E402


class FakeApi:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, **kwargs):
        self.messages.append(text)


def test_send_full_report_sends_data_and_llm_placeholder():
    api = FakeApi()
    # LLM-секция реально вызовет балансер — для теста это не нужно,
    # поэтому проверяем только структуру с патчем llm_section
    import tg_bot.trading_report as mod

    orig_llm = mod.llm_section
    mod.llm_section = lambda snap: ["🤖 тестовая аналитика"]
    try:
        send_full_report(api, 123)
    finally:
        mod.llm_section = orig_llm
    assert api.messages, "сообщения не отправлены"
    assert any("Главное за 30 секунд" in m for m in api.messages)
    assert "⏳ LLM-аналитика готовится…" in api.messages


def test_accounts_routes_trading_text_before_treasury():
    src = (Path(__file__).resolve().parents[1] / "tg_bot" / "accounts.py").read_text(encoding="utf-8")
    # перехват стоит ДО treasury-интента (логика — в seam-модуле)
    pos_trading = src.index("pre_treasury_intents(api, chat_id, text)")
    pos_treasury = src.index("_handle_treasury_intent(api, chat_id, text)")
    assert pos_trading < pos_treasury
    assert "from tg_bot.pre_treasury_intents import pre_treasury_intents" in src


def test_pre_treasury_seam_handles_trading_and_freelance(monkeypatch):
    import sys
    import types

    import tg_bot.pre_treasury_intents as seam

    calls = []

    class FakeApi:
        def send_message(self, chat_id, text, **kwargs):
            calls.append(("msg", chat_id, text[:30]))

    api = FakeApi()

    # фриланс-путь: подменяем dashboard-модуль (импорт внутри seam)
    fake_dash = types.ModuleType("tg_bot.dashboard")
    fake_dash._handle_freelance_summary_intent = lambda a, cid, text: False
    monkeypatch.setitem(sys.modules, "tg_bot.dashboard", fake_dash)

    import tg_bot.trading_report as tr
    monkeypatch.setattr(tr, "is_trading_button_text", lambda t: bool(t) and "трейдинг" in t.casefold())
    monkeypatch.setattr(tr, "send_full_report", lambda api, cid: calls.append(("report", cid, None)))
    assert seam.pre_treasury_intents(api, 1, "📈 Трейдинг") is True
    assert any(c[0] == "report" for c in calls)
    assert seam.pre_treasury_intents(api, 1, "сколько стоит аренда") is False


def test_trading_button_text_detector():
    from tg_bot.trading_report import is_trading_button_text

    assert is_trading_button_text("📈 Трейдинг")
    assert is_trading_button_text("трейдинг")
    assert is_trading_button_text("Трейдинг отчёт")
    assert not is_trading_button_text("крипто заработок")
    assert not is_trading_button_text(None)


def test_callbacks_use_shared_helper():
    src = (Path(__file__).resolve().parents[1] / "tg_bot" / "callbacks.py").read_text(encoding="utf-8")
    assert "from tg_bot.trading_report import send_full_report" in src
