"""Tests for the detailed trading report module."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tg_bot.trading_report import _chunks, format_report, prompt_for_llm  # noqa: E402


def _snapshot() -> dict:
    return {
        "generated_at": "2026-08-19 10:00 UTC",
        "directional": {
            "ok": True,
            "arms": {
                "main": {"closed": 5, "wins": 1, "realized": -7.73, "gross": -2.76,
                         "fees": 2.98, "win_rate": 20.0, "open_positions": 0,
                         "equity": 9992.27, "dd_pct": 0.096, "entry_mode": "enabled",
                         "recent_trades": [{"exchange": "kraken", "symbol": "ATOM",
                                            "reason": "stop_loss", "net_pnl_usd": -3.12}]},
                "control": {"closed": 5, "wins": 0, "realized": -12.64, "gross": -7.7,
                            "fees": 2.97, "win_rate": 0.0, "open_positions": 0,
                            "equity": 9987.36, "dd_pct": 0.126, "entry_mode": "enabled",
                            "recent_trades": []},
            },
        },
        "dca": {
            "VA main": {"mode": "va", "weekly": 300, "value": 100.34, "deposited": 100.0,
                        "fees": 0.1, "date": "2026-08-18"},
            "control": {"mode": "dca", "weekly": 100, "value": 100.18, "deposited": 100.0,
                        "fees": 0.1, "date": "2026-08-18"},
        },
        "basket": {"value": 998.44, "pnl_pct": -0.156, "invested": 1000.0, "fees": 1.0,
                   "date": "2026-08-18", "weights_rule": "inverse_vol_30d", "cash": 0.0},
        "t2": {"legs": {"BTC": {"position": "CASH", "equity": 25473.13,
                                 "cash_equiv": 23444.97, "trades": 68,
                                 "last_signal": "2026-08-19"}},
               "portfolio": {"date": "2026-08-19", "portfolio": 26668.71, "bh": 25772.21}},
        "freqtrade": {"open": [("BTC/USDT", 64540.94, None, "2026-08-18 00:00:00", 645.41)],
                      "closed": 0},
        "mm": {"snapshots": 5816805, "span_h": 86.5, "trade_flow": 418458,
               "btc_touch_life_s": 5.6, "btc_fill60_q2000": 0.1812},
        "scoreboard": {"date": "2026-08", "dv2": {"pnl_pct": -0.38, "trades": 9},
                       "market_mean_pct": -7.35, "top10_basket_pct": 2.51,
                       "verdict": {"winner": "top10_basket", "best_momentum": None}},
        "services": {"aios-quant-trading": "active", "aios-orderbook-ws": "active",
                     "aios-freqtrade-t2-dry": "failed"},
    }


def test_format_report_covers_all_sections():
    snap = _snapshot()
    chunks = format_report(snap)
    text = "\n".join(chunks)
    # человеческие маркеры: главное, объяснения, словарик
    assert "Главное за 30 секунд" in text
    assert "Что это" in text
    assert "Робот А" in text and "Робот Б" in text
    assert "Автокопилка" in text and "Корзина топ-10" in text
    assert "Моментум-роботы" in text and "вне рынка (кэш)" in text
    assert "freqtrade" in text and "BTC/USDT" in text
    assert "снимков" in text and "5,816,805" in text
    assert "Кто лучший по тесту" in text and "корзина топ-10" in text
    assert "Словарик" in text
    assert "Простыми словами" in text
    assert "⚠️ лежит: aios-freqtrade-t2-dry" in text


def test_format_report_human_verdict_names_winner():
    snap = _snapshot()
    text = "\n".join(format_report(snap))
    # победитель переведён на человеческий язык
    assert "Победитель: <b>корзина топ-10</b>" in text


def test_format_report_no_crash_on_empty():
    snap = {"generated_at": "x", "directional": {"arms": {}, "ok": False},
            "dca": {}, "basket": {}, "t2": {"legs": {}, "portfolio": None},
            "freqtrade": {"open": [], "closed": 0}, "mm": {},
            "scoreboard": None, "services": {}}
    chunks = format_report(snap)
    assert len(chunks) == 1
    assert "нет данных" in chunks[0] or "0/0" in chunks[0]


def test_chunks_split_and_respect_limit():
    text = "\n".join(f"line {i}" for i in range(2000))
    chunks = _chunks(text, limit=1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)
    assert "".join(chunks).count("line ") == 2000


def test_chunks_single_short_message():
    assert _chunks("короткий текст", limit=1000) == ["короткий текст"]


def test_prompt_for_llm_contains_key_numbers():
    snap = _snapshot()
    prompt = prompt_for_llm(snap)
    assert "Directional v2 main" in prompt
    assert "-7.73$" in prompt or "-7.73" in prompt
    assert "inverse_vol_30d" in prompt
    assert "top10_basket" in prompt


def test_prompt_for_llm_no_crash_on_empty():
    snap = {"directional": {"arms": {}}, "dca": {}, "basket": {},
            "t2": {"legs": {}}, "freqtrade": {"open": [], "closed": 0},
            "mm": {}, "scoreboard": None}
    assert "Состояние трейдинг-контуров" in prompt_for_llm(snap)


def test_nav_trading_wired_to_report():
    from pathlib import Path as _P

    src = _P("/root/AIOS/tg_bot/callbacks.py").read_text(encoding="utf-8")
    assert 'data == "nav_trading"' in src
    assert "from tg_bot.trading_report import send_full_report" in src
