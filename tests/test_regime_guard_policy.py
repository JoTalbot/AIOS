"""Tests: режимный guard в политике входов."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aios_core.quant_directional_policy import (  # noqa: E402
    DirectionalV2Config,
    entry_block_reason,
)


def _kwargs():
    return {
        "exchange": "kucoin",
        "global_positions": 0,
        "exchange_positions": 0,
        "drawdown_pct": 0.0,
        "daily_loss_pct": 0.0,
        "candle_is_new": True,
    }


def _analysis():
    return {"signal": "BUY_LONG", "confidence": 0.90, "ml_prob_up": 0.70, "rl_position": 0.60}


def test_regime_guard_blocks_entries_in_crash(tmp_path):
    regime_file = tmp_path / "regime.json"
    regime_file.write_text(json.dumps({"regime": "CRASH"}))
    config = DirectionalV2Config(entry_mode="enabled", regime_guard=True,
                                 regime_file=str(regime_file))
    assert entry_block_reason(config, _analysis(), **_kwargs()) == "regime_crash_kill"


def test_regime_guard_allows_in_bear(tmp_path):
    regime_file = tmp_path / "regime.json"
    regime_file.write_text(json.dumps({"regime": "BEAR"}))
    config = DirectionalV2Config(entry_mode="enabled", regime_guard=True,
                                 regime_file=str(regime_file))
    assert entry_block_reason(config, _analysis(), **_kwargs()) is None


def test_regime_guard_disabled_by_default(tmp_path):
    regime_file = tmp_path / "regime.json"
    regime_file.write_text(json.dumps({"regime": "CRASH"}))
    config = DirectionalV2Config(entry_mode="enabled", regime_guard=False,
                                 regime_file=str(regime_file))
    assert entry_block_reason(config, _analysis(), **_kwargs()) is None


def test_regime_guard_fail_open_on_missing_file(tmp_path):
    config = DirectionalV2Config(entry_mode="enabled", regime_guard=True,
                                 regime_file=str(tmp_path / "nope.json"))
    assert entry_block_reason(config, _analysis(), **_kwargs()) is None


def test_regime_guard_checked_after_freeze(tmp_path):
    regime_file = tmp_path / "regime.json"
    regime_file.write_text(json.dumps({"regime": "CRASH"}))
    config = DirectionalV2Config(entry_mode="freeze", regime_guard=True,
                                 regime_file=str(regime_file))
    assert entry_block_reason(config, _analysis(), **_kwargs()) == "entry_mode_freeze"
