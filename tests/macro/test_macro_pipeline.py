#!/usr/bin/env python3
"""Local tests for macro/derivatives pipeline (before prod deploy)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))

from fetch_market_data import Collector
from fetch_derivatives import parse_klines, parse_lsr, parse_oi, DerivCollector
from analyze_predictive import align, eval_feature

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


def fixture_transport(fixtures: dict[str, Path]):
    def transport(url: str, timeout: int = 25) -> bytes:
        for key, p in fixtures.items():
            if key in url:
                return p.read_bytes()
        raise AssertionError(f"no fixture for {url}")
    return transport


def test_yahoo_parse():
    print("\n[M1] парсинг Yahoo chart")
    fx = fixture_transport({"chart": T / "fixtures" / "yahoo_chart.json"})
    c = Collector(transport=fx)
    rows = c.fetch_yahoo("BTC_USD", 10)
    check("3 точки", len(rows) == 3)
    check("значения", [r["value"] for r in rows] == [60000.0, 61000.5, 60500.25])
    check("даты корректны", rows[0]["date"] == "2026-08-01")


def test_blockchain_parse():
    print("\n[M2] парсинг blockchain.info")
    fx = fixture_transport({"charts/hash-rate": T / "fixtures" / "blockchain_chart.json"})
    c = Collector(transport=fx)
    rows = c.fetch_blockchain("hashrate", 10)
    check("3 точки", len(rows) == 3)
    check("значения", rows[1]["value"] == 362000.5)


def test_binance_parse():
    print("\n[M3] парсинг Binance (klines/lsr/oi)")
    k = parse_klines((T / "fixtures" / "binance_klines.json").read_bytes())
    check("3 бара", len(k) == 3)
    check("taker_buy_ratio 1-й бар", abs(k[0]["taker_buy_ratio"] - 66.2 / 123.5) < 1e-9)
    check("taker_buy_ratio 2-й бар", abs(k[1]["taker_buy_ratio"] - 48.0 / 98.1) < 1e-9)
    lsr = parse_lsr((T / "fixtures" / "binance_lsr.json").read_bytes())
    check("lsr: 3 записи, первая 1.10", len(lsr) == 3 and lsr[0]["lsr"] == 1.10)
    oi = parse_oi((T / "fixtures" / "binance_oi.json").read_bytes())
    check("oi: 2 записи, oi 106200", len(oi) == 2 and oi[1]["oi"] == 106200.0)


def test_deriv_collector():
    print("\n[M4] DerivCollector с фикстурами")
    fx = fixture_transport({
        "klines": T / "fixtures" / "binance_klines.json",
        "globalLongShortAccountRatio": T / "fixtures" / "binance_lsr.json",
        "openInterestHist": T / "fixtures" / "binance_oi.json",
        "premiumIndex": T / "fixtures" / "binance_premium.json",
    })
    dc = DerivCollector(transport=fx)
    check("klines", len(dc.klines("BTC", 10)) == 3)
    check("global_lsr", len(dc.global_lsr("BTC")) == 3)
    check("oi", len(dc.oi_hist("BTC")) == 2)
    p = dc.premium("BTC")
    check("premium mark", p["mark"] == 60400.5 and p["index"] == 60399.9)


def test_align_no_lookahead():
    print("\n[M5] align: лаги без lookahead")
    # цена: 3 дня; фича: известна на t0
    price = {1785600000: 100.0, 1785686400: 105.0, 1785772800: 103.0}
    feat = {1785600000: 1.0}
    x, y = align(feat, price, lag_hours=24, step_hours=24)
    check("1 пара (t0 фича -> ret t1..t2)", len(x) == 1 and len(y) == 1)
    check("ret = (103/105-1) = -1.905%", abs(y[0] - (-1.90476)) < 1e-3)
    # лаг 48ч: фича t0 -> ret t2..t3 (нет t3) -> пусто
    x2, y2 = align(feat, price, lag_hours=48, step_hours=24)
    check("лаг 48ч без будущего -> пусто", len(x2) == 0)


def test_synthetic_signal():
    print("\n[M6] синтетика: фича коррелирует с будущим ret")
    rng = np.random.default_rng(7)
    n = 200
    ts = [1785600000 + i * 86400 for i in range(n)]
    feat = {t: rng.normal(0, 1) for t in ts}
    # цена: ret между t_i и t_{i+1} зависит от фичи В ДЕНЬ t_{i-1} (лаг 1 день)
    price = {}
    px = 100.0
    for i, t in enumerate(ts):
        price[t] = px
        if i + 1 < n:
            f_prev = feat[ts[i - 1]] if i >= 1 else 0.0
            ret = 0.5 * f_prev + rng.normal(0, 0.5)
            px = px * (1 + ret / 100)
    x, y = align(feat, price, lag_hours=24, step_hours=24)
    corr = float(np.corrcoef(x, y)[0, 1])
    check(f"корреляция на синтетике {corr:+.2f} > 0.2", corr > 0.2, f"got {corr}")


def test_hourly_normalization():
    print("\n[M8] часовая нормализация load_series")
    import analyze_predictive as ap
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "BTC_USD_1h.jsonl"
        with open(p, "w") as f:
            for h in range(4):
                f.write(json.dumps({"ts": 1785600000 + h * 3600, "value": 100.0 + h}) + "\n")
        day = ap.load_series(p)
        hour = ap.load_series(p, gran="hour")
        check("day-нормализация схлопывает в 1", len(day) == 1)
        check("hour-нормализация сохраняет 4", len(hour) == 4)


def test_real_fixture_analysis():
    print("\n[M7] анализ на фикстурах (пайплайн end-to-end)")
    with tempfile.TemporaryDirectory() as tmp:
        dd = Path(tmp)
        # BTC цена: 3 дня
        price = {1785600000: 100.0, 1785686400: 105.0, 1785772800: 103.0}
        with open(dd / "BTC_USD.jsonl", "w") as f:
            for t, v in price.items():
                f.write(json.dumps({"ts": t, "value": v}) + "\n")
        # DXY: 2 значения
        with open(dd / "DXY.jsonl", "w") as f:
            for t, v in [(1785600000, 100.0), (1785686400, 101.0)]:
                f.write(json.dumps({"ts": t, "value": v}) + "\n")
        import analyze_predictive as ap
        dxy = ap.load_series(dd / "DXY.jsonl")
        bt = ap.load_series(dd / "BTC_USD.jsonl")
        x, y = ap.align(dxy, bt, 24, 24)
        check("1 совпадение DXY->BTC", len(x) == 1)
        res = ap.eval_feature("DXY", dxy, bt, 24, 24, min_n=1)
        check("eval_feature вернул результат", res is not None and "corr" in res)


if __name__ == "__main__":
    test_yahoo_parse()
    test_blockchain_parse()
    test_binance_parse()
    test_deriv_collector()
    test_align_no_lookahead()
    test_synthetic_signal()
    test_hourly_normalization()
    test_real_fixture_analysis()
    print(f"\n===== ИТОГ: PASS {PASS} / FAIL {FAIL} =====")
    sys.exit(1 if FAIL else 0)
