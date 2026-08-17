"""Tests for the triple-barrier label helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.quant_ml_triple_barrier import (  # noqa: E402
    barrier_sim,
    next_bar_labels,
    triple_barrier_labels,
)


def test_tp_first_gives_label_1():
    close = np.array([100.0, 101.0, 102.5, 102.0, 101.5])  # +2.5% бар => TP
    high = np.array([100.0, 101.5, 102.5, 102.5, 102.0])
    low = np.array([100.0, 100.5, 101.0, 101.0, 101.0])
    y, close_at = triple_barrier_labels(high, low, close, timeout=24)
    assert y[0] == 1
    assert close_at[0] == 2


def test_sl_first_gives_label_0():
    close = np.array([100.0, 99.5, 99.0, 98.5])  # -1.0% на баре 2 => SL
    high = np.array([100.0, 100.0, 99.6, 99.0])
    low = np.array([100.0, 99.2, 99.0, 98.4])
    y, close_at = triple_barrier_labels(high, low, close, timeout=24)
    assert y[0] == 0
    assert close_at[0] == 2


def test_both_barriers_same_bar_prefers_sl():
    close = np.array([100.0, 101.0])
    high = np.array([100.0, 103.0])  # трогает и TP и SL в одном баре
    low = np.array([100.0, 98.0])
    y, _ = triple_barrier_labels(high, low, close, timeout=24)
    assert y[0] == 0  # консервативно


def test_timeout_uses_close_sign():
    close = np.array([100.0, 100.2, 100.1, 100.4])
    high = np.array([100.0, 100.5, 100.5, 100.6])
    low = np.array([100.0, 99.9, 99.9, 100.0])
    y, close_at = triple_barrier_labels(high, low, close, timeout=2)
    assert close_at[0] == 2  # таймаут на 2-м баре
    assert y[0] == 1  # close вырос


def test_next_bar_labels():
    close = np.array([100.0, 101.0, 100.5])
    y, close_at = next_bar_labels(close)
    assert y.tolist() == [1, 0]
    assert close_at.tolist() == [1, 2]


def test_barrier_sim_net_of_cost():
    close = np.array([100.0] * 30)
    high = close * 1.03
    low = close * 0.99
    res = barrier_sim(np.array([0.95]), 0.9, high, low, close)
    assert res["n"] == 1
    assert abs(res["mean_pct"] - (2.0 - 0.5)) < 1e-6  # TP 2% - 0.5% cost
