"""Tests for A/B power analysis and basket benchmark helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.quant_ab_report import (  # noqa: E402
    basket_benchmark,
    required_trades_for_power,
)


def test_power_monotonic_in_effect():
    n_small = required_trades_for_power(0.1, 2.0)
    n_big = required_trades_for_power(0.3, 2.0)
    assert n_big < n_small
    assert n_small > 100  # слабый эффект требует много сделок


def test_power_scales_with_variance():
    n_lo = required_trades_for_power(0.2, 1.0)
    n_hi = required_trades_for_power(0.2, 2.0)
    assert n_hi > n_lo


def test_basket_benchmark_reads_last_row(tmp_path):
    f = tmp_path / "basket.jsonl"
    f.write_text('{"day":"2026-08-16","value_usd":990.0,"pnl_pct":-1.0,"fees_paid_usd":1.0}\n'
                 '{"day":"2026-08-17","value_usd":1025.0,"pnl_pct":2.5,"fees_paid_usd":1.2}\n',
                 encoding="utf-8")
    b = basket_benchmark(f)
    assert b == {"value_usd": 1025.0, "pnl_pct": 2.5, "fees_paid_usd": 1.2}


def test_basket_benchmark_missing_file():
    assert basket_benchmark(Path("/nonexistent/x.jsonl")) is None
