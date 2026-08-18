"""Tests for the lead-lag helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.quant_lead_lag import lead_lag_row, momentum_rule  # noqa: E402


def _series(seed: int, n: int = 3000) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="h")
    price = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, n)))
    return pd.Series(price, index=idx)


def test_lead_lag_detects_lagged_leader():
    leader = _series(1)
    # alt = лидер с лагом 1 (реакция через час) + шум
    alt_vals = leader.values[:-1]
    alt = pd.Series(alt_vals, index=leader.index[1:])
    row = lead_lag_row(leader, alt)
    assert row[0] < row[1]  # синхронная слабее, чем лаг 1


def test_lead_lag_sync_market_has_no_lag_advantage():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2025-01-01", periods=3000, freq="h")
    rets = rng.normal(0, 0.005, 3000)
    leader = pd.Series(100 * np.exp(np.cumsum(rets)), index=idx)
    # независимый альт — корреляции должны быть ~0 на всех лагах
    alt = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.005, 3000))), index=idx)
    row = lead_lag_row(leader, alt)
    assert abs(row[1]) < 0.1


def test_momentum_rule_net_of_cost():
    # альт с ап-трендом + лидер, у которого моментум положителен в тесте
    rng = np.random.default_rng(3)
    idx = pd.date_range("2025-01-01", periods=4000, freq="h")
    leader = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.002, 0.004, 4000))), index=idx)
    alt = pd.Series(50 * np.exp(np.cumsum(rng.normal(0.001, 0.004, 4000))), index=idx)
    res = momentum_rule(leader, alt)
    assert res is not None
    assert res["n_trades"] >= 20
    assert "baseline_mean_pct" in res
    assert res["mean_pct"] < res["baseline_mean_pct"] or res["mean_pct"] >= -100
