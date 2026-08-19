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
    # перехват стоит ДО treasury-интента
    pos_trading = src.index('_t_norm in ("трейдинг"')
    pos_treasury = src.index("_handle_treasury_intent(api, chat_id, text)")
    assert pos_trading < pos_treasury
    assert "send_full_report" in src


def test_callbacks_use_shared_helper():
    src = (Path(__file__).resolve().parents[1] / "tg_bot" / "callbacks.py").read_text(encoding="utf-8")
    assert "from tg_bot.trading_report import send_full_report" in src
