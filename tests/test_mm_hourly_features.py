"""Tests for the hourly microstructure aggregator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.mm_hourly_features import aggregate_hour, hour_bucket  # noqa: E402


def _snap(bid, ask, bd, ad):
    return (bid, ask, (bid + ask) / 2.0, bd, ad)


def test_hour_bucket():
    assert hour_bucket(3600.0) == 1
    assert hour_bucket(3600 * 25 + 59) == 25


def test_aggregate_hour_balanced_flow():
    snaps = [_snap(100.0, 100.1, 1000.0, 1000.0)] * 3600  # симметричный стакан
    trades = [(0, 100.0, 100.0), (5, 50.0, 50.0)]  # buy = sell
    f = aggregate_hour(snaps, trades)
    assert f["n_snapshots"] == 3600
    assert f["obi1_mean"] == 0.0
    assert f["depth_imb_mean"] == 0.5
    assert abs(f["taker_buy_frac"] - 0.5) < 1e-9
    assert f["spread_mean_bps"] > 0
    assert f["mid_ret"] == 0.0


def test_aggregate_hour_buy_heavy():
    snaps = [_snap(100.0, 100.1, 900.0, 1100.0)] * 3600
    trades = [(0, 300.0, 100.0)]
    f = aggregate_hour(snaps, trades)
    assert f["obi1_mean"] < 0  # спрос тоньше -> obi < 0
    assert f["depth_imb_mean"] < 0.5
    assert abs(f["taker_buy_frac"] - 0.75) < 1e-9


def test_aggregate_hour_no_trades():
    snaps = [_snap(100.0, 100.1, 1000.0, 1000.0)] * 3600
    f = aggregate_hour(snaps, [])
    assert f["taker_buy_frac"] is None
    assert f["n_trade_buckets"] == 0
