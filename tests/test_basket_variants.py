"""Tests for basket variants pure helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.quant_basket_variants import (  # noqa: E402
    metrics,
    simulate_dca,
    simulate_rebalance,
    stitch_ton,
    trend_filter_mask,
    vol_weights,
)


def test_stitch_ton_normalizes_at_overlap():
    idx = pd.date_range("2026-01-01", periods=10, freq="D")
    binance = pd.Series(np.linspace(100, 109, 10), index=idx)
    idx2 = pd.date_range("2026-01-08", periods=5, freq="D")
    kraken = pd.Series(np.linspace(200, 204, 5), index=idx2)  # другой масштаб
    stitched = stitch_ton(binance, kraken)
    # binance до 08.01, kraken (нормализованный) после
    assert stitched.index.min() == idx.min()
    assert stitched.index.max() == idx2.max()
    # в точке стыка значения близки (нормализация)
    assert abs(stitched.loc[idx2[0]] - binance.loc[idx2[0]]) < 1e-6


def test_trend_filter_mask():
    idx = pd.date_range("2026-01-01", periods=250, freq="D")
    btc = pd.Series(100.0 + np.arange(250) * 0.1, index=idx)  # восходящий
    mask = trend_filter_mask(btc, window=200)
    assert mask.iloc[-1]  # выше SMA200 в конце
    # в начале NaN -> False
    assert not bool(mask.iloc[0])


def test_vol_weights_normalize_and_invert():
    idx = pd.date_range("2026-01-01", periods=60, freq="D")
    rng = np.random.default_rng(0)
    prices = pd.DataFrame({
        "A": 100 * np.exp(np.cumsum(rng.normal(0, 0.05, 60))),
        "B": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 60))),
    }, index=idx)
    w = vol_weights(prices, idx[-1], window=30)
    assert abs(w.sum() - 1.0) < 1e-9
    assert w["A"] < w["B"]  # более волатильный -> меньший вес


def test_metrics_on_known_equity():
    idx = pd.date_range("2026-01-01", periods=10, freq="D")
    eq = pd.Series([1000, 1010, 1020, 1030, 1020, 1040, 1050, 1060, 1070, 1080], index=idx)
    m = metrics(eq)
    assert abs(m["total_pct"] - 8.0) < 1e-9
    assert m["max_dd_pct"] < 0  # была просадка 1030 -> 1020
    assert m["final_equity"] == 1080.0


def test_simulate_dca_flat_market_counts_buys():
    idx = pd.date_range("2026-01-01", periods=30, freq="D")
    prices = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)
    eq, n = simulate_dca(prices, weekly=25.0)
    assert n == 4  # 4 недели в 30 днях
    # плоский рынок, комиссии съедают: итог чуть меньше 1000
    assert eq.iloc[-1] < 1000.0


def test_simulate_rebalance_flat_market_only_fees():
    idx = pd.date_range("2026-01-01", periods=90, freq="D")
    prices = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)
    eq, n = simulate_rebalance(prices, "monthly")
    assert n > 0  # ребалансы были
    assert eq.iloc[-1] <= 1000.0
