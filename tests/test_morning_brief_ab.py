"""Tests for the morning-brief A/B paper line."""

from __future__ import annotations

import json

import run_morning_brief as brief


def _portfolio(closed: int, pnl: float) -> dict:
    return {
        "binance": {"closed_trades": closed, "realized_pnl_usd": pnl},
        "_risk_state": {},
    }


def test_ab_line_reads_both_portfolios(tmp_path):
    main_p = tmp_path / "main.json"
    ctrl_p = tmp_path / "control.json"
    main_p.write_text(json.dumps(_portfolio(3, 1.25)))
    ctrl_p.write_text(json.dumps(_portfolio(1, -2.5)))
    line = brief._ab_paper_line(main_p, ctrl_p)
    assert "main 3 сд. (+1.25$)" in line
    assert "control 1 сд. (-2.50$)" in line


def test_ab_line_missing_files_returns_none(tmp_path):
    assert brief._ab_paper_line(tmp_path / "no.json", tmp_path / "no2.json") is None


def test_ab_line_ignores_risk_state_and_cross_arb():
    data = {
        "binance": {"closed_trades": 2, "realized_pnl_usd": 0.5},
        "cross_arbitrage": {"closed_trades": 99, "realized_pnl_usd": 999},
        "_risk_state": {},
    }
    import tempfile
    from pathlib import Path
    p = Path(tempfile.mkdtemp()) / "p.json"
    p.write_text(json.dumps(data))
    line = brief._ab_paper_line(p, p)
    assert "2 сд." in line and "99" not in line.split("|")[0]
