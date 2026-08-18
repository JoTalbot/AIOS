"""Tests for the best-move changes (vol-targeting basket + bear regime)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_basket_paper import inverse_vol_weights  # noqa: E402
from run_morning_brief import btc_regime  # noqa: E402


def test_inverse_vol_weights_low_vol_gets_more():
    rng = np.random.default_rng(1)
    n = 40
    calm = list(np.exp(np.cumsum(rng.normal(0, 0.002, n))))
    wild = list(np.exp(np.cumsum(rng.normal(0, 0.02, n))))
    w = inverse_vol_weights({"A": calm, "B": wild}, window=30)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["A"] > w["B"]  # спокойный актив получает больший вес
    assert w["A"] > 0 and w["B"] > 0


def test_inverse_vol_weights_short_history_zero_weight():
    rng = np.random.default_rng(2)
    calm = list(np.exp(np.cumsum(rng.normal(0, 0.005, 40))))
    w = inverse_vol_weights({"A": calm, "B": [1.0, 2.0]}, window=30)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["A"] == 1.0  # единственный с волатильностью
    assert w["B"] == 0.0  # недостаточно истории


def test_inverse_vol_weights_all_unknown_equal_fallback():
    w = inverse_vol_weights({"A": [1.0], "B": [2.0]}, window=30)
    assert abs(w["A"] - 0.5) < 1e-9 and abs(w["B"] - 0.5) < 1e-9


def _regime_csv(tmp_path, direction: int) -> Path:
    import pandas as pd

    n = 220
    close = 100.0 + direction * np.arange(n) * 0.1
    df = pd.DataFrame({
        "timestamp_ms": (pd.Timestamp("2026-01-01").value // 10**6
                         + np.arange(n) * 86_400_000),  # один бар в день
        "close": close,
    })
    p = tmp_path / "BTC_1h.csv"
    df.to_csv(p, index=False)
    return p


def test_btc_regime_bear(tmp_path):
    assert btc_regime(_regime_csv(tmp_path, direction=-1)) == "bear"


def test_btc_regime_bull(tmp_path):
    assert btc_regime(_regime_csv(tmp_path, direction=+1)) == "bull"


def test_btc_regime_short_data(tmp_path):
    p = tmp_path / "BTC_1h.csv"
    p.write_text("timestamp_ms,close\n1,100\n2,101\n", encoding="utf-8")
    assert btc_regime(p) is None


def test_btc_regime_missing_file(tmp_path):
    assert btc_regime(tmp_path / "nope.csv") is None
