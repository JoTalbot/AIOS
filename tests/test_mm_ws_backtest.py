"""Tests for the ws MM backtest driver (pure helpers)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.mm_ws_backtest import _decimate, latency_stats  # noqa: E402


def test_decimate_keeps_first_row_per_bucket():
    rows = [(1.0,), (1.2,), (1.5,), (2.0,), (2.6,), (3.4,)]
    out = _decimate(rows, min_interval=0.9)
    assert [r[0] for r in out] == [1.0, 2.0, 3.4]


def test_decimate_empty():
    assert _decimate([], 0.9) == []


def test_latency_stats_quantiles_and_share():
    snaps = [{"latency_ms": v} for v in (100, 200, 300, 400, 0, 0)]
    s = latency_stats(snaps)
    assert s["n"] == 4
    assert s["share_pct"] == 66.7
    assert s["median_ms"] == 250.0  # median of 100,200,300,400
    assert s["p90_ms"] == 400.0


def test_latency_stats_no_measurements():
    assert latency_stats([{"latency_ms": 0.0}]) == {"n": 0}
