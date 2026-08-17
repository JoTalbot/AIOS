"""Tests for the long-horizon signal check (pure helpers)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.mm_signal_long_horizon_check import (  # noqa: E402
    _labels,
    _momenta,
    bootstrap_auc,
    purge_split,
)


def test_labels_match_direction_over_horizon():
    times = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    mids = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    valid, mov, y = _labels(mids, times, H=2)
    assert valid[:4].all() and not valid[4:].any()
    assert y[:4].all()  # strictly rising -> all up
    # flat mid -> not mov
    valid2, mov2, _ = _labels(np.array([100.0, 100.0, 100.0]), np.array([0.0, 1.0, 2.0]), H=1)
    assert valid2[0] and not mov2[0]


def test_momenta_are_relative_returns():
    mids = np.array([100.0, 101.0, 102.0, 103.0])
    m = _momenta(mids, [2])
    assert abs(m["mom2"][2] - 0.02 * 1e4) < 1e-9
    assert m["mom2"][0] == 0.0  # underfilled lag -> 0


def test_purge_split_closes_train_before_test():
    times = np.arange(0.0, 100.0, 1.0)
    valid = np.ones(100, dtype=bool)
    mov = np.ones(100, dtype=bool)
    tr, te = purge_split(times, valid, mov, H=10, split_t=50.0, stride=1)
    assert (times[tr] + 10 < 50.0).all()
    assert (times[te] >= 50.0).all()


def test_purge_split_stride_thins_test_only():
    times = np.arange(0.0, 100.0, 1.0)
    valid = np.ones(100, dtype=bool)
    mov = np.ones(100, dtype=bool)
    tr, te = purge_split(times, valid, mov, H=10, split_t=50.0, stride=4)
    assert len(te) <= 13  # 50..99 -> 50 obs, stride 4 -> 13
    assert (np.diff(times[te]) == 4.0).all()


def test_bootstrap_auc_sane():
    rng = np.random.default_rng(0)
    y = (rng.random(400) > 0.5).astype(float)
    p = y * 0.8 + (1 - y) * 0.2 + rng.normal(0, 0.05, 400)
    mean, std = bootstrap_auc(y, p, n_boot=50)
    assert 0.8 < mean <= 1.0
    assert std >= 0.0
