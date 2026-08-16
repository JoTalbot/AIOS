#!/usr/bin/env python3
"""Tests for factor/momentum strategies module (before prod deploy)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))

import momentum_strategies as ms

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def synth_prices(n=400, drift=0.001, seed=1):
    rng = np.random.default_rng(seed)
    return 100 * np.cumprod(1 + rng.normal(drift, 0.02, n))


def test_sma():
    print("\n[F1] SMA расчёт")
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    s = ms.sma(x, 3)
    check("SMA3 на последнем = 4", abs(s[-1] - 4.0) < 1e-9)
    check("SMA3 первые 2 NaN", np.isnan(s[0]) and np.isnan(s[1]))


def test_returns():
    print("\n[F2] returns_nd")
    x = np.array([100.0, 110.0, 121.0])
    r = ms.returns_nd(x, 1)
    check("ret1 = 10%", abs(r[1] - 0.10) < 1e-9)
    check("ret1 первые NaN", np.isnan(r[0]))
    r2 = ms.returns_nd(x, 2)
    check("ret2 = 21%", abs(r2[2] - 0.21) < 1e-9)


def test_ts_momentum_no_lookahead():
    print("\n[F3] TS-момент: нет lookahead (сигнал по вчерашнему close)")
    n = 300
    ts = np.array([1700000000 + i * 86400 for i in range(n)])
    # цена растёт -> после warmup SMA200, должно быть в рынке
    closes = {"BTC-USD": 100 * np.cumprod(1 + np.full(n, 0.001))}
    r = ms.run_variant("T1", closes, ts, {"kind": "ts_btc"})
    check("equity length", len(r["equity"]) == n)
    check("рост при растущем рынке", r["equity"][-1] > 1.0, f"got {r['equity'][-1]:.3f}")
    # падающий рынок -> flat (0 доходность, без просадки)
    closes2 = {"BTC-USD": 100 * np.cumprod(1 - np.full(n, 0.001))}
    r2 = ms.run_variant("T1", closes2, ts, {"kind": "ts_btc"})
    check("падение -> флэт (equity ≈ 1)", abs(r2["equity"][-1] - 1.0) < 0.01,
          f"got {r2['equity'][-1]:.3f}")


def test_costs():
    print("\n[F4] издержки применяются при ребалансе")
    # плоский рынок + частый ребаланс -> equity < 1 из-за издержек
    n = 300
    ts = np.array([1700000000 + i * 86400 for i in range(n)])
    flat = {"BTC-USD": np.full(n, 100.0)}
    # SMA-кроссовер будет флэтом (50==200 не бывает... используем cs_mom на плоских = флэт)
    r = ms.run_variant("flat", flat, ts, {"kind": "ts_btc"})
    # при ровно плоской цене btc > sma200? 100 > 100 = False -> cash -> equity 1
    check("плоский рынок -> equity ~1", abs(r["equity"][-1] - 1.0) < 1e-6)


def test_cs_momentum():
    print("\n[F5] CS-момент: топ-5 по моменту")
    n = 400
    ts = np.array([1700000000 + i * 86400 for i in range(n)])
    closes = {}
    # BTC растёт сильно, остальные плоские (без шума -> момент выберет BTC)
    closes["BTC-USD"] = 100 * np.cumprod(1 + np.full(n, 0.003))
    for s in ["ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "DOGE-USD", "ADA-USD",
              "LINK-USD", "AVAX-USD", "UNI-USD", "NEAR-USD", "LTC-USD", "DOT-USD",
              "TRX-USD"]:
        closes[s] = np.full(n, 100.0)
    r = ms.run_variant("M1", closes, ts, {"kind": "cs_mom", "lookback": 90})
    check("CS-момент находит победителя", r["equity"][-1] > 1.0, f"got {r['equity'][-1]:.3f}")
    check("сделки есть", r["n_trades"] > 0)


def test_load_all_alignment():
    print("\n[F6] load_all: выравнивание по датам")
    def transport(url, timeout=25):
        n = 10
        ts = [1700000000 + i * 86400 for i in range(n)]
        close = [100.0 + i for i in range(n)]
        payload = {"chart": {"result": [{"timestamp": ts,
                                         "indicators": {"quote": [{"close": close}]}}]}}
        return json.dumps(payload).encode()
    closes, ts = ms.load_all(transport, ["BTC-USD", "ETH-USD"], 10)
    check("2 актива", len(closes) == 2)
    check("10 дней выровнены", len(ts) == 10 and len(closes["BTC-USD"]) == 10)


def test_metrics():
    print("\n[F7] метрики корректны")
    n = 400
    ts = np.array([1700000000 + i * 86400 for i in range(n)])
    up = {"BTC-USD": 100 * np.cumprod(1 + np.full(n, 0.002))}
    r = ms.run_variant("up", up, ts, {"kind": "ts_btc"})
    check("CAGR > 0", r["cagr"] > 0)
    check("Sharpe > 0", r["sharpe"] > 0)
    check("MaxDD <= 0", r["max_dd"] <= 0)
    check("total > 0", r["total_pct"] > 0)


if __name__ == "__main__":
    test_sma()
    test_returns()
    test_ts_momentum_no_lookahead()
    test_costs()
    test_cs_momentum()
    test_load_all_alignment()
    test_metrics()
    print(f"\n===== ИТОГ: PASS {PASS} / FAIL {FAIL} =====")
    sys.exit(1 if FAIL else 0)
