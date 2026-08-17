"""Tests for the maker-fee sensitivity helper."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.mm_maker_fee_sensitivity import breakeven_fee  # noqa: E402


def test_breakeven_interpolates_crossing():
    pts = [(-0.0002, -50.0), (0.0, -20.0), (0.0005, 30.0)]
    be = breakeven_fee(pts)
    assert be is not None and -0.0 <= be < 0.0005
    # linear: crosses between 0.0 (-20) and 0.0005 (+30): t = 20/50 = 0.4
    assert abs(be - 0.0002) < 1e-9


def test_breakeven_none_when_no_crossing():
    assert breakeven_fee([(0.0, 10.0), (0.0005, 20.0)]) is None
    assert breakeven_fee([(0.0, -10.0), (0.0005, -20.0)]) is None


def test_breakeven_unsorted_input_is_sorted():
    pts = [(0.0005, 30.0), (-0.0002, -50.0), (0.0, -20.0)]
    be = breakeven_fee(pts)
    assert abs(be - 0.0002) < 1e-9


def test_breakeven_exact_zero_point():
    assert breakeven_fee([(0.0, 0.0), (0.0005, 10.0)]) == 0.0
