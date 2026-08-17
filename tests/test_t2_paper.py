#!/usr/bin/env python3
"""Tests for T2 paper loop (before prod deploy)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))

import run_t2_momentum as t2

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


def make_rows(n=120, drift=0.001, seed=1, start_close=100.0):
    """Synthetic daily closes."""
    rng = np.random.default_rng(seed)
    closes = [start_close]
    for i in range(1, n):
        closes.append(closes[-1] * (1 + drift + rng.normal(0, 0.02)))
    import time
    base = 1700000000
    rows = []
    for i, c in enumerate(closes):
        rows.append({"date": time.strftime("%Y-%m-%d", time.gmtime(base + i * 86400)),
                     "close": float(c)})
    return rows


def test_signal():
    print("\n[T1] сигнал close vs SMA50")
    rows = make_rows(120, drift=0.005)  # растущий рынок
    sig = t2.compute_signal(rows)
    check("длинный тренд -> LONG", sig["signal"] == "LONG", str(sig))
    rows2 = make_rows(120, drift=-0.005)
    sig2 = t2.compute_signal(rows2)
    check("падающий тренд -> CASH", sig2["signal"] == "CASH", str(sig2))
    # мало истории
    rows3 = make_rows(30)
    sig3 = t2.compute_signal(rows3)
    check("мало истории -> CASH (reason)", sig3["signal"] == "CASH" and sig3["sma50"] is None)


def test_fetch_fallback():
    print("\n[T2] fetch_closes: Yahoo + фолбэк Binance")
    n = 120
    yahoo_payload = {"chart": {"result": [{
        "timestamp": [1700000000 + i * 86400 for i in range(n)],
        "indicators": {"quote": [{"close": [100.0 + i for i in range(n)]}]}}]}}

    def transport(url, timeout=25):
        if "yahoo" in url:
            return json.dumps(yahoo_payload).encode()
        raise AssertionError("no binance needed")

    rows = t2.fetch_closes(transport)
    check("Yahoo работает", len(rows) == n and rows[-1]["close"] == 100.0 + n - 1)

    # Yahoo падает -> Binance
    binance_payload = [[(1700000000 + i * 86400) * 1000, "0", "0", "0",
                        str(200.0 + i), "0", 0, "0", 0, "0", "0", "0"] for i in range(n)]

    def transport2(url, timeout=25):
        if "yahoo" in url:
            raise RuntimeError("yahoo down")
        return json.dumps(binance_payload).encode()

    rows2 = t2.fetch_closes(transport2)
    check("фолбэк Binance", len(rows2) == n and rows2[-1]["close"] == 200.0 + n - 1)

    # оба падают -> исключение
    def transport3(url, timeout=25):
        raise RuntimeError("all down")

    try:
        t2.fetch_closes(transport3)
        check("исключение при обоих сбоях", False)
    except RuntimeError:
        check("исключение при обоих сбоях", True)


def test_daily_idempotent():
    print("\n[T3] идемпотентность (повторный запуск не дублирует)")
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        log = Path(tmp) / "log.jsonl"
        rows = make_rows(120, drift=0.005)
        r1 = t2.run_daily(state, log, rows)
        check("первый запуск ok", r1["status"] == "ok")
        n1 = len(log.read_text().splitlines())
        r2 = t2.run_daily(state, log, rows)
        check("повторный — already_processed", r2["status"] == "already_processed")
        n2 = len(log.read_text().splitlines())
        check("лог не задвоился", n1 == n2 == 1, f"{n1} vs {n2}")


def test_position_change_costs():
    print("\n[T4] смена позиции: издержки и трейды")
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        log = Path(tmp) / "log.jsonl"
        # растущий рынок: первый запуск войдёт в LONG
        rows_up = make_rows(120, drift=0.005)
        r1 = t2.run_daily(state, log, rows_up)
        check("вход в LONG", r1["position"] == "LONG")
        st = json.loads(state.read_text())
        check("издержки 0.15% применены (вход)", abs(st["equity"] - 10000 * 0.9985) < 1e-6,
              f"equity {st['equity']}")
        check("трейд записан", len(st["trades"]) == 1)
        check("entry_price = close", st["entry_price"] == rows_up[-1]["close"])
        # теперь падающий рынок: новые данные -> выход в CASH.
        # последний день делаем плоским (close == prev), чтобы изолировать издержки
        rows_down = rows_up[:-1] + make_rows(60, drift=-0.01, start_close=rows_up[-1]["close"] * 0.95)
        rows_down[-1] = dict(rows_down[-2])
        eq_before_exit = json.loads(state.read_text())["equity"]
        r2 = t2.run_daily(state, log, rows_down)
        check("выход в CASH", r2["position"] == "CASH")
        st = json.loads(state.read_text())
        check("издержки 0.15% при выходе", abs(st["equity"] - eq_before_exit * 0.9985) < 1e-6,
              f"{st['equity']} vs {eq_before_exit*0.9985}")
        check("2 трейда", len(st["trades"]) == 2)
        check("exit: entry_price None", st["entry_price"] is None)
        check("equity > 0 (сохранена)", st["equity"] > 0)


def test_equity_marking():
    print("\n[T5] equity: close/close в позиции")
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        log = Path(tmp) / "log.jsonl"
        # входим в LONG
        rows_up = make_rows(120, drift=0.005)
        t2.run_daily(state, log, rows_up)
        st0 = json.loads(state.read_text())
        eq0 = st0["equity"]
        # следующий день: цена +1% -> equity должна вырасти на 1%
        last = rows_up[-1]
        nxt = {"date": "2099-01-01", "close": last["close"] * 1.01}
        rows2 = rows_up + [nxt]
        r = t2.run_daily(state, log, rows2)
        st = json.loads(state.read_text())
        check("equity *1.01 в позиции", abs(st["equity"] - eq0 * 1.01) < 1e-6,
              f"{st['equity']} vs {eq0*1.01}")


def test_bh_reference():
    print("\n[T6] buy&hold эталон (cash_equiv)")
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        log = Path(tmp) / "log.jsonl"
        rows = make_rows(120, drift=0.005)
        t2.run_daily(state, log, rows)
        st = json.loads(state.read_text())
        exp_bh = 10000.0 * rows[-1]["close"] / rows[-2]["close"]
        check("cash_equiv = close[-1]/close[-2]", abs(st["cash_equiv"] - exp_bh) < 1e-6,
              f"{st['cash_equiv']} vs {exp_bh}")
        # повторный запуск того же дня не меняет cash_equiv (идемпотентность)
        t2.run_daily(state, log, rows)
        st2 = json.loads(state.read_text())
        check("идемпотентность BH", abs(st2["cash_equiv"] - st["cash_equiv"]) < 1e-9)


def test_log_format():
    print("\n[T7] формат лога")
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        log = Path(tmp) / "log.jsonl"
        rows = make_rows(120, drift=0.005)
        t2.run_daily(state, log, rows)
        entry = json.loads(log.read_text().splitlines()[0])
        for k in ("date", "close", "sma50", "signal", "position", "equity", "bh_equity"):
            check(f"поле {k}", k in entry)


if __name__ == "__main__":
    test_signal()
    test_fetch_fallback()
    test_daily_idempotent()
    test_position_change_costs()
    test_equity_marking()
    test_bh_reference()
    test_log_format()
    print(f"\n===== ИТОГ: PASS {PASS} / FAIL {FAIL} =====")
    sys.exit(1 if FAIL else 0)
