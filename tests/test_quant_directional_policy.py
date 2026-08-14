"""Pure tests for fail-closed directional-v2 policy."""

from __future__ import annotations

import pytest

from aios_core.quant_directional_policy import (
    DirectionalV2Config,
    bearish_exit_confirmed,
    entry_block_reason,
    portfolio_equity,
)


def _allowed(**overrides):
    config = DirectionalV2Config(entry_mode="enabled", require_ml=True, **overrides)
    analysis = {"signal": "BUY_LONG", "confidence": 0.90, "ml_prob_up": 0.70, "rl_position": 0.60}
    return config, analysis


def test_default_policy_freezes_entries(monkeypatch):
    monkeypatch.delenv("AIOS_QUANT_ENTRY_MODE", raising=False)
    config = DirectionalV2Config.from_env()

    assert config.entry_mode == "freeze"
    assert config.max_global_positions == 2
    assert config.max_positions_per_exchange == 1
    assert config.round_trip_cost_pct(0.0015) == pytest.approx(0.5)


def test_entry_gate_requires_cost_aware_signal_confirmation():
    config, analysis = _allowed()
    kwargs = {
        "exchange": "kucoin",
        "global_positions": 0,
        "exchange_positions": 0,
        "drawdown_pct": 0.0,
        "daily_loss_pct": 0.0,
        "candle_is_new": True,
    }

    assert entry_block_reason(config, analysis, **kwargs) is None
    assert entry_block_reason(config, {**analysis, "confidence": 0.7}, **kwargs) == "confidence_below_min"
    assert entry_block_reason(config, {**analysis, "ml_prob_up": 0.55}, **kwargs) == "ml_not_confirmed"
    assert entry_block_reason(config, {**analysis, "rl_position": 0.1}, **kwargs) == "rl_veto"
    assert entry_block_reason(config, analysis, **{**kwargs, "drawdown_pct": 0.5}) == "global_drawdown_kill"
    assert entry_block_reason(config, analysis, **{**kwargs, "global_positions": 2}) == "global_position_limit"
    assert entry_block_reason(config, analysis, **{**kwargs, "unpriced_positions": 1}) == "unpriced_positions"


def test_execution_prices_include_conservative_costs():
    config = DirectionalV2Config(half_spread_rate=0.001, slippage_rate=0.0005)

    assert config.entry_execution_price(100.0) == pytest.approx(100.15)
    assert config.exit_execution_price(100.0) == pytest.approx(99.85)


def test_portfolio_equity_marks_positions_and_counts_unpriced():
    data = {
        "kraken": {
            "initial_balance_usd": 1_000.0,
            "cash_usd": 800.0,
            "positions": {
                "BTCUSD": {"qty": 2.0, "entry_price": 100.0},
                "ETHUSD": {"qty": 1.0, "entry_price": 50.0},
            },
        }
    }

    initial, equity, unpriced = portfolio_equity(data, {"kraken": {"BTC": 110.0}}, ("kraken",))

    assert initial == 1_000.0
    assert equity == pytest.approx(1_070.0)
    assert unpriced == 1


def test_bearish_signal_requires_hold_confidence_and_ml_confirmation():
    config = DirectionalV2Config(min_confidence=0.8, min_hold_seconds=3_600, bearish_ml_max=0.4)
    analysis = {"signal": "SELL_SHORT", "confidence": 0.9, "ml_prob_up": 0.3}

    assert bearish_exit_confirmed(config, analysis, held_seconds=3_601)
    assert not bearish_exit_confirmed(config, analysis, held_seconds=100)
    assert not bearish_exit_confirmed(config, {**analysis, "ml_prob_up": 0.5}, held_seconds=3_601)
