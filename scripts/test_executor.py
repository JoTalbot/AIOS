#!/usr/bin/env python3
"""Tests for run_t2_executor.py (real-money scaffold) with mocked transport.

Run: pytest test_executor.py
"""

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_t2_executor import (  # noqa: E402
    DEFAULT_CONFIG, State, compute_signal, fetch_closes, main,
)

# ---------------------------------------------------------------- unit tests

def _fake_klines_transport(close_series):
    """Returns a transport returning Binance-style klines ending with close_series."""
    import base64

    def t(url, timeout=25):
        if "yahoo" in url:
            raise RuntimeError("should not fall back")
        # build N=400 klines ending with the given closes
        base = 100.0
        closes = close_series
        n = 400
        start = int(time.time() * 1000) - n * 86400000
        klines = []
        for i in range(n):
            c = closes[i - (400 - len(closes))] if i >= 400 - len(closes) else base
            klines.append([start + i * 86400000, c, c, c, c, "1000", start + i * 86400000,
                           "0", "100", "0", "0", "0"])
        return json.dumps(klines).encode()

    return t


def test_compute_signal_no_lookahead():
    rows = [{"date": f"2026-01-{i:02d}", "close": 100.0 + i} for i in range(1, 400)]
    sig, s_in, s_out = compute_signal(rows, 50, 40)
    assert sig == "LONG"  # last close (498) > sma50 (~398.5)
    assert abs(s_in - 474.5) < 1e-6
    rows2 = [{"date": f"2026-01-{i:02d}", "close": 500.0 - i} for i in range(1, 400)]
    sig2, _, _ = compute_signal(rows2, 50, 40)
    assert sig2 == "CASH"


def test_fetch_closes_binance():
    rows = fetch_closes("BTC/USDT", transport=_fake_klines_transport([200.0] * 5))
    assert len(rows) >= 60
    assert rows[-1]["close"] == 200.0


def test_main_dry_no_orders(tmp_path):
    """Dry mode must not call the exchange and must record state."""
    cfg = tmp_path / "cfg.json"
    state_file = tmp_path / "state.json"
    cfg.write_text(json.dumps({
        "symbols": ["BTC/USDT"],
        "windows": {},
        "state_file": str(state_file),
        "max_daily_orders": 4,
        "api_key": "", "api_secret": "",
    }))
    # uptrend -> LONG
    transport = _fake_klines_transport([110.0 + i * 0.1 for i in range(5)])
    old_argv = sys.argv
    sys.argv = ["run_t2_executor.py", "--dry", "--config", str(cfg)]
    try:
        import run_t2_executor as m
        m._default_transport = lambda *a, **k: transport("https://api.binance.com", 25)
        rc = main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    st = json.loads(state_file.read_text())
    assert st["positions"]["BTC/USDT"] == "LONG"
    assert st["orders_today"] == 1


def test_main_live_executes_and_caps(tmp_path, monkeypatch):
    """Live mode calls the exchange; daily cap respected."""
    cfg = tmp_path / "cfg.json"
    state_file = tmp_path / "state.json"
    cfg.write_text(json.dumps({
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "windows": {},
        "state_file": str(state_file),
        "max_daily_orders": 1,
        "api_key": "k", "api_secret": "s",
    }))
    transport = _fake_klines_transport([110.0 + i * 0.1 for i in range(5)])

    class FakeEx:
        def __init__(self):
            self.orders = []

        def fetch_balance(self):
            return {"USDT": {"free": 10000.0}}

        def fetch_ticker(self, sym):
            return {"last": 100.0}

        def create_market_buy_order(self, sym, amount):
            self.orders.append(("buy", sym, amount))

        def create_market_sell_order(self, sym, amount):
            self.orders.append(("sell", sym, amount))

    fake = FakeEx()
    monkeypatch.setattr("run_t2_executor._make_exchange", lambda cfg: fake)
    monkeypatch.setattr("run_t2_executor._default_transport",
                        lambda *a, **k: transport("https://api.binance.com", 25))
    old_argv = sys.argv
    sys.argv = ["run_t2_executor.py", "--live", "--config", str(cfg)]
    try:
        rc = main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    assert len(fake.orders) == 1, f"cap=1 but {len(fake.orders)} orders"
    assert fake.orders[0][0] == "buy"
    st = json.loads(state_file.read_text())
    assert st["orders_today"] == 1
    # second run same day: cap reached -> no new orders
    fake2 = FakeEx()
    monkeypatch.setattr("run_t2_executor._make_exchange", lambda cfg: fake2)
    sys.argv = ["run_t2_executor.py", "--live", "--config", str(cfg)]
    try:
        rc = main()
    finally:
        sys.argv = old_argv
    assert len(fake2.orders) == 0
    assert rc == 0


def test_live_requires_keys(tmp_path, capsys):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"symbols": ["BTC/USDT"], "api_key": "", "api_secret": ""}))
    old_argv = sys.argv
    sys.argv = ["run_t2_executor.py", "--live", "--config", str(cfg)]
    try:
        rc = main()
    finally:
        sys.argv = old_argv
    assert rc == 2


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
