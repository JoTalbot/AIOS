"""Tests for the basket paper benchmark."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_basket_paper import rebalance  # noqa: E402

TOP10 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "TRX", "TON", "ADA", "LINK"]


def test_first_rebalance_invests_cash_equally():
    state = {"cash_usd": 1000.0, "holdings": {}, "fees_paid_usd": 0.0}
    prices = {sym: 100.0 for sym in TOP10}
    rebalance(state, "2026-08-17", prices)
    for sym in TOP10:
        assert abs(state["holdings"][sym] - 1.0) < 1e-9  # $100 each / $100 px
    # 10 legs * $100 * 0.1% = $1.0 списано с кэша (честный денежный поток)
    assert abs(state["cash_usd"] + 1.0) < 1e-9
    assert abs(state["fees_paid_usd"] - 1.0) < 1e-9
    assert state["last_rebalance"] == "2026-08-17"


def test_monthly_rebalance_pays_fees_only_on_traded_value():
    state = {
        "cash_usd": 0.0,
        "holdings": {sym: 1.0 for sym in TOP10},
        "fees_paid_usd": 0.0,
    }
    prices = {sym: 200.0 for sym in TOP10}  # value 2000, target 200/sym
    rebalance(state, "2026-09-01", prices)
    # каждое плечо торгуется с 1.0 -> 1.0 qty? нет: target_qty = 200/200 = 1.0
    for sym in TOP10:
        assert abs(state["holdings"][sym] - 1.0) < 1e-9
    assert state["fees_paid_usd"] == 0.0  # ничего не торговалось


def test_rebalance_trades_when_prices_diverge():
    state = {
        "cash_usd": 0.0,
        "holdings": {sym: 1.0 for sym in TOP10},
        "fees_paid_usd": 0.0,
    }
    prices = {"BTC": 400.0}
    prices.update({sym: 200.0 for sym in TOP10 if sym != "BTC"})
    # value = 400 + 9*200 = 2200; target = 220/sym
    rebalance(state, "2026-09-01", prices)
    # BTC: 1.0 -> 220/400 = 0.55 (продажа), остальные 1.0 -> 1.1 (покупка)
    assert abs(state["holdings"]["BTC"] - 0.55) < 1e-9
    assert abs(state["holdings"]["ETH"] - 1.1) < 1e-9
    assert state["fees_paid_usd"] > 0
