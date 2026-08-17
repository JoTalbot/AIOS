#!/usr/bin/env python3
"""Tests for the 2-year backtest module (before prod)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))

import backtest_2y as b2

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


def test_fetch_pagination():
    print("\n[B1] fetch_klines пагинация (2 страницы)")
    # генерируем 3000 klines (2 страницы по 1500)
    def gen(n, t0):
        rows = []
        for i in range(n):
            rows.append([t0 + i * 3600000, "100", "101", "99", str(100 + i * 0.001),
                         "1", t0 + (i + 1) * 3600000 - 1, "100", 10, "0.5", "50", "0"])
        return rows

    page1 = gen(1500, 1700000000000)
    page2 = gen(500, 1700000000000 + 1500 * 3600000)
    calls = {"n": 0}

    def transport(url, timeout=25):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps(page1).encode()
        return json.dumps(page2).encode()

    rows = b2.fetch_klines(transport, "BTC", 100)
    check("2 вызова транспорта", calls["n"] == 2)
    check("2000 баров собрано", len(rows) == 2000)
    check("ts монотонны", all(rows[i]["ts"] < rows[i + 1]["ts"] for i in range(len(rows) - 1)))


def test_record_analyze():
    print("\n[B2] record_and_analyze сигналы")
    # бычий паттерн
    rng = np.random.default_rng(1)
    closes = [100 + i * 0.5 for i in range(50)]
    an = b2.record_and_analyze(closes, 0.8)
    check("восходящий тренд -> BUY_LONG", an["signal"] == "BUY_LONG", str(an))
    closes2 = [100 - i * 0.5 for i in range(50)]
    an2 = b2.record_and_analyze(closes2, 0.2)
    check("нисходящий тренд -> SELL_SHORT", an2["signal"] == "SELL_SHORT", str(an2))
    check("confidence в [0,1]", 0 <= an["confidence"] <= 1)


def test_engine_basic():
    print("\n[B3] движок: базовая симуляция")
    n = 3000
    t0 = 1700000000000
    times = np.array([t0 + i * 3600000 for i in range(n)])
    # цена: медленный рост -> сигналы BUY, потом резкий рост на +3% (TP)
    closes = np.array([100 + i * 0.02 for i in range(n)])
    # вставить +3% скачок на баре 500
    closes[500:] = closes[500] * 1.03
    highs = closes * 1.002
    lows = closes * 0.998
    series = {"BTC": {"closes": closes, "highs": highs, "lows": lows, "times": times}}
    probs = {"BTC": np.full(n, 0.7)}
    res = b2.run_engine(series, probs, start_idx=100)
    check("сделки есть", len(res["trades"]) > 0, f"got {len(res['trades'])}")
    check("PnL корректный тип", isinstance(res["pnl"], float))


def test_engine_no_lookahead():
    print("\n[B4] движок: вход только с start_idx")
    n = 300
    times = np.array([1700000000000 + i * 3600000 for i in range(n)])
    closes = np.array([100.0] * n)
    series = {"BTC": {"closes": closes, "highs": closes, "lows": closes, "times": times}}
    probs = {"BTC": np.full(n, 0.9)}
    res = b2.run_engine(series, probs, start_idx=200)
    # история warmup до start_idx, входы только после
    check("нет сделок в warmup (нет сигналов в flat)", len(res["trades"]) == 0)


def test_build_features():
    print("\n[B5] build_features: 13 фич, без NaN на хвосте")
    closes = np.array([100 + i * 0.1 for i in range(500)], dtype=float)
    X = b2.build_features(closes)
    check("форма (500, 13)", X.shape == (500, 13))
    check("хвост без NaN", not np.isnan(X[-10:]).any())
    check("первые 24 NaN (недостаточно истории)", np.isnan(X[:24]).all())


def test_train_predict_oos():
    print("\n[B6] train_and_predict: OOS-сплит (train 70%, NaN на train)")
    rng = np.random.default_rng(3)
    n = 2000
    closes = 100 * np.cumprod(1 + rng.normal(0.0001, 0.01, n))
    series = {"BTC": {"closes": closes, "highs": closes * 1.001,
                      "lows": closes * 0.999,
                      "times": np.array([1700000000000 + i * 3600000 for i in range(n)])}}
    probs = b2.train_and_predict(series)
    p = probs["BTC"]
    check("probs длина", len(p) == n)
    check("train-часть NaN", np.isnan(p[:int(n * 0.7)]).all())
    check("OOS-часть числа", not np.isnan(p[int(n * 0.7):]).all())


def test_engine_kill_switch():
    print("\n[B7] kill-свитч: drawdown 0.25% блокирует входы")
    n = 2000
    times = np.array([1700000000000 + i * 3600000 for i in range(n)])
    # цена падает на 50% -> drawdown > 0.25% -> после первого убытка входов нет
    closes = np.array([100 * (0.9995 ** i) for i in range(n)])
    series = {"BTC": {"closes": closes, "highs": closes, "lows": closes, "times": times}}
    probs = {"BTC": np.full(n, 0.9)}
    res = b2.run_engine(series, probs, start_idx=100)
    # после срабатывания drawdown входы блокируются: сделок заметно меньше,
    # чем при нормальном рынке (B3 дал > 0 при росте)
    check("kill-switch ограничивает сделки", len(res["trades"]) <= 12,
          f"got {len(res['trades'])}")
    # и большинство — стопы в начале (до срабатывания kill)
    reasons = [t["reason"] for t in res["trades"]]
    check("доминируют стопы", reasons.count("stop_loss") >= len(reasons) // 2,
          f"{reasons}")


if __name__ == "__main__":
    test_fetch_pagination()
    test_record_analyze()
    test_engine_basic()
    test_engine_no_lookahead()
    test_build_features()
    test_train_predict_oos()
    test_engine_kill_switch()
    print(f"\n===== ИТОГ: PASS {PASS} / FAIL {FAIL} =====")
    sys.exit(1 if FAIL else 0)
