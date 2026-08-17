#!/usr/bin/env python3
"""2-year backtest: 'what if trading started 2 years ago'.

Collects 1h klines from Binance Futures for the universe (2 years, paginated),
then simulates the CURRENT Directional v2 engine rules on daily-aggregated or
hourly data as close as possible to the live config:

  - entry: BUY_LONG signal from record_and_analyze (replica) + ML gate
    (CatBoost trained on the FIRST 70% of each symbol's history - honest OOS),
    confidence >= 0.88, fixed $200/leg, max 1 global position;
  - exits: TP 2% / SL 1% / trail 1.0 (current live config) + bearish exit;
  - kill switches: drawdown & daily loss 0.25% of equity;
  - costs: fee 0.15% + half-spread 0.05% + slippage 0.05% (round-trip ~0.5%).

WINDOW: last 2 years (2024-08-15 .. 2026-08-15). Train/test per symbol:
train = first 70% of the 2y window, test = last 30% (~7 months OOS).

Transport injectable for tests. Usage:
    python backtest_2y.py [--symbols BTC ETH SOL] [--out data/reports/backtest_2y.md]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

FAPI = "https://fapi.binance.com"
UA = {"User-Agent": "Mozilla/5.0"}

PROFILE = {
    "min_confidence": 0.88,
    "ml_min_prob_up": 0.65,
    "take_profit_pct": 0.02,
    "stop_loss_pct": -0.01,
    "trail_ratio": 1.0,
    "min_hold_seconds": 7200,
    "fee_rate": 0.0015,
    "cost_rate": 0.0010,  # half-spread + slippage
    "max_global_positions": 1,
    "max_drawdown_pct": 0.25,
    "max_daily_loss_pct": 0.25,
    "stake": 200.0,
}

WINDOW_DAYS = 730
TRAIN_FRAC = 0.70


def default_transport(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_klines(transport, symbol: str, days: int) -> list[dict]:
    """Paginated 1h klines over the last `days` days."""
    out = []
    start = int(time.time() * 1000) - days * 86400 * 1000
    while True:
        url = (f"{FAPI}/fapi/v1/klines?symbol={symbol}USDT&interval=1h"
               f"&startTime={start}&limit=1500")
        raw = transport(url)
        rows = json.loads(raw.decode())
        if not rows:
            break
        for k in rows:
            out.append({"ts": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]), "close": float(k[4]),
                        "volume": float(k[5])})
        if len(rows) < 1500:
            break
        start = rows[-1][0] + 3600 * 1000
        time.sleep(0.15)
    return out


# ------------------------------------------------------------- engine replica


def record_and_analyze(closes: list[float], ml_prob: float | None) -> dict:
    """1:1 replica of the live signal engine (fast/bb/rsi/macd scoring)."""
    prices = closes[-50:]
    fast_period = min(3, len(prices))
    slow_period = min(10, len(prices))
    sma_fast = sum(prices[-fast_period:]) / fast_period
    sma_slow = sum(prices[-slow_period:]) / slow_period
    rsi = 50.0
    if len(prices) >= 5:
        gains = [max(prices[i] - prices[i - 1], 0) for i in range(1, len(prices))]
        losses = [max(prices[i - 1] - prices[i], 0) for i in range(1, len(prices))]
        avg_gain = sum(gains[-14:]) / min(14, len(gains))
        avg_loss = sum(losses[-14:]) / min(14, len(losses))
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100.0 - 100.0 / (1.0 + rs)
        else:
            rsi = 100.0
    period_bb = min(20, len(prices))
    sma_bb = sum(prices[-period_bb:]) / period_bb
    var = sum((p - sma_bb) ** 2 for p in prices[-period_bb:]) / period_bb
    std = var ** 0.5
    upper = sma_bb + 2 * std
    lower = sma_bb - 2 * std
    p12 = prices[-min(12, len(prices)):]
    p26 = prices[-min(26, len(prices)):]
    macd = sum(p12) / len(p12) - sum(p26) / len(p26)
    cur = prices[-1]
    bullish = bearish = 0
    if cur <= lower:
        bullish += 2
    elif cur >= upper:
        bearish += 2
    if rsi < 35:
        bullish += 2
    elif rsi > 65:
        bearish += 2
    if sma_fast > sma_slow:
        bullish += 1
    elif sma_fast < sma_slow:
        bearish += 1
    if macd > 0:
        bullish += 1
    elif macd < 0:
        bearish += 1
    if ml_prob is not None:
        if ml_prob >= 0.65:
            bullish += 1
        elif ml_prob <= 0.35:
            bearish += 1
    if bullish >= 3 and bullish > bearish:
        return {"signal": "BUY_LONG",
                "confidence": round(min(0.99, 0.70 + bullish * 0.06), 2)}
    if bearish >= 3 and bearish > bullish:
        return {"signal": "SELL_SHORT",
                "confidence": round(min(0.99, 0.70 + bearish * 0.06), 2)}
    return {"signal": "HOLD", "confidence": 0.50}


def run_engine(series: dict[str, dict], probs: dict[str, np.ndarray],
               start_idx: int) -> dict:
    """Event-driven 1h simulation, max 1 global position, kill switches."""
    p = PROFILE
    cash = 10000.0
    initial = cash
    peak = cash
    trades = []
    positions: dict[str, dict] = {}
    history: dict[str, list[float]] = {s: [] for s in series}
    day = ""
    day_start = initial

    def equity() -> float:
        eq = cash
        for pos in positions.values():
            eq += pos["qty"] * pos["mark"]
        return eq

    all_ts = sorted({int(ts) for s in series.values()
                     for ts in s["times"][start_idx:]})
    # warmup
    for sym, s in series.items():
        history[sym] = [float(c) for c in s["closes"][:start_idx]]

    for ts in all_ts:
        d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        if d != day:
            day = d
            day_start = equity()
        # exits
        for sym, s in series.items():
            k = int(np.searchsorted(s["times"], ts))
            if k >= len(s["closes"]):
                continue
            px = float(s["closes"][k])
            history[sym].append(px)
            pos = positions.get(sym)
            if pos is None:
                continue
            pos["mark"] = px
            entry = pos["entry"]
            max_seen = max(pos["max_seen"], px)
            pos["max_seen"] = max_seen
            hi, lo = float(s["highs"][k]), float(s["lows"][k])
            exit_px = None
            reason = ""
            if lo <= entry * (1 + p["stop_loss_pct"]):
                exit_px = entry * (1 + p["stop_loss_pct"]) * (1 - p["cost_rate"])
                reason = "stop_loss"
            elif hi >= entry * (1 + p["take_profit_pct"]):
                exit_px = entry * (1 + p["take_profit_pct"]) * (1 - p["cost_rate"])
                reason = "take_profit"
            elif max_seen > entry * 1.01 and lo <= max_seen * p["trail_ratio"]:
                exit_px = max_seen * p["trail_ratio"] * (1 - p["cost_rate"])
                reason = "trailing_stop"
            else:
                ml = float(probs[sym][k]) if k < len(probs[sym]) else None
                an = record_and_analyze(history[sym], ml)
                if (an["signal"] == "SELL_SHORT"
                        and an["confidence"] >= p["min_confidence"]
                        and ml is not None and ml <= 0.40
                        and (ts - pos["opened_at"]) >= p["min_hold_seconds"] * 1000):
                    exit_px = px * (1 - p["cost_rate"])
                    reason = "bearish_exit"
            if exit_px is not None:
                proceeds = exit_px * pos["qty"]
                net = proceeds - pos["invested"] - exit_px * pos["qty"] * p["fee_rate"]
                cash += proceeds - exit_px * pos["qty"] * p["fee_rate"]
                trades.append({"sym": sym, "net": net, "reason": reason,
                               "opened_at": pos["opened_at"], "ts": ts})
                del positions[sym]
        # entries
        eq = equity()
        peak = max(peak, eq)
        dd = max(0.0, (initial - eq) / initial * 100.0)
        daily = max(0.0, (day_start - eq) / day_start * 100.0)
        if dd >= p["max_drawdown_pct"] or daily >= p["max_daily_loss_pct"]:
            continue
        for sym, s in series.items():
            if len(positions) >= p["max_global_positions"]:
                break
            k = int(np.searchsorted(s["times"], ts))
            if k >= len(s["closes"]):
                continue
            px = float(s["closes"][k])
            ml = float(probs[sym][k]) if k < len(probs[sym]) else None
            an = record_and_analyze(history[sym], ml)
            if an["signal"] != "BUY_LONG" or an["confidence"] < p["min_confidence"]:
                continue
            if ml is None or ml < p["ml_min_prob_up"]:
                continue
            invested = min(cash * 0.2, p["stake"])
            if invested < 10:
                continue
            exec_px = px * (1 + p["cost_rate"])
            qty = (invested - invested * p["fee_rate"]) / exec_px
            cash -= invested
            positions[sym] = {"entry": px, "qty": qty, "invested": invested,
                              "max_seen": px, "opened_at": ts, "mark": px}
    final = equity()
    return {"initial": initial, "final": final, "pnl": final - initial,
            "trades": trades}


def build_features(closes: np.ndarray) -> np.ndarray:
    """13 scale-free features (same as live ML model)."""
    n = len(closes)
    out = np.full((n, 13), np.nan)
    for i in range(24, n):
        c = closes[max(0, i - 100):i + 1]
        ret1 = c[-1] / c[-2] - 1 if len(c) > 1 else 0
        ret3 = c[-1] / c[-4] - 1 if len(c) > 3 else 0
        ret6 = c[-1] / c[-7] - 1 if len(c) > 6 else 0
        ret12 = c[-1] / c[-13] - 1 if len(c) > 12 else 0
        ret24 = c[-1] / c[-25] - 1 if len(c) > 24 else 0
        chg = np.diff(c)
        up = np.clip(chg, 0, None)
        dn = np.clip(-chg, 0, None)
        ag = up[-14:].mean() if len(up) >= 14 else up.mean()
        al = dn[-14:].mean() if len(dn) >= 14 else dn.mean()
        rsi = 100.0 - 100.0 / (1 + ag / (al + 1e-9)) if al > 0 else 100.0
        sma20 = c[-20:].mean() if len(c) >= 20 else c.mean()
        sd20 = c[-20:].std() if len(c) >= 20 else 0.0
        bb_pos = (c[-1] - sma20 + 2 * sd20) / (4 * sd20 + 1e-9)
        ema12 = float(np.mean(c[-12:]))
        ema26 = float(np.mean(c[-26:]))
        macd_norm = (ema12 - ema26) / c[-1]
        ema_gap = (ema12 - ema26) / c[-1]
        vol = np.abs(chg[-20:]).mean() if len(chg) >= 20 else 0.0
        vol_now = abs(chg[-1]) if len(chg) else 0.0
        vol_ratio = vol_now / (vol + 1e-9)
        out[i] = [ret1, ret3, ret6, ret12, ret24, rsi, bb_pos, macd_norm, ema_gap,
                  vol_ratio, 0.0, (c[-1] - c.min()) / (c.max() - c.min() + 1e-9),
                  (c[-1] - c[-2]) / c[-2] if len(c) > 1 else 0]
    return out


def train_and_predict(series: dict[str, dict]) -> dict[str, np.ndarray]:
    """Per-symbol CatBoost on first 70%, predict on the rest (OOS)."""
    from catboost import CatBoostClassifier

    probs: dict[str, np.ndarray] = {}
    for sym, s in series.items():
        closes = s["closes"]
        n = len(closes)
        cut = int(n * TRAIN_FRAC)
        X = build_features(closes)
        y = (np.roll(closes, -1) > closes).astype(int)
        y[-1] = 0
        tr = slice(100, cut - 48)
        if np.unique(y[tr]).size < 2:
            probs[sym] = np.full(n, 0.5)
            continue
        m = CatBoostClassifier(iterations=200, depth=4, learning_rate=0.05,
                               loss_function="Logloss", eval_metric="AUC",
                               random_seed=42, verbose=0)
        ok = ~np.isnan(X[tr]).any(axis=1)
        m.fit(X[tr][ok], y[tr][ok])
        p = m.predict_proba(X)[:, 1]
        p[:cut] = np.nan
        probs[sym] = p
    return probs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbols", nargs="+",
                    default=["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "LINK"])
    ap.add_argument("--transport", default=None)
    ap.add_argument("--out", type=Path, default=Path("data/reports/backtest_2y.md"))
    args = ap.parse_args()

    transport = default_transport if args.transport is None else args.transport
    print(f"сбор данных: {len(args.symbols)} активов x {WINDOW_DAYS} дней...", flush=True)
    series: dict[str, dict] = {}
    for sym in args.symbols:
        rows = fetch_klines(transport, sym, WINDOW_DAYS)
        if len(rows) < 1000:
            print(f"  {sym}: мало данных ({len(rows)})", flush=True)
            continue
        series[sym] = {
            "closes": np.array([r["close"] for r in rows]),
            "highs": np.array([r["high"] for r in rows]),
            "lows": np.array([r["low"] for r in rows]),
            "times": np.array([r["ts"] for r in rows]),
        }
        print(f"  {sym}: {len(rows)} баров", flush=True)
    print(f"готово серий: {len(series)}", flush=True)

    probs = train_and_predict(series)
    # OOS: только последние 30% окна
    start_idx = int(len(series[args.symbols[0]]["closes"]) * TRAIN_FRAC)
    res = run_engine(series, probs, start_idx)
    trades = res["trades"]
    wins = [t for t in trades if t["net"] > 0]
    gw = sum(t["net"] for t in wins)
    gl = -sum(t["net"] for t in trades if t["net"] < 0)
    print(f"\nРЕЗУЛЬТАТ (OOS, последние ~30% из 2 лет):")
    print(f"  сделок: {len(trades)}, winrate: {len(wins)/len(trades)*100:.1f}%"
          if trades else "  сделок: 0")
    print(f"  PnL: {res['pnl']:+.2f}$ (старт $10k -> финал ${res['final']:.2f})")
    if gl > 0:
        print(f"  profit factor: {gw/gl:.2f}")
    from collections import Counter
    print(f"  причины выхода: {dict(Counter(t['reason'] for t in trades))}")
    # BH сравнение
    bh = (series[args.symbols[0]]["closes"][-1] /
          series[args.symbols[0]]["closes"][start_idx] - 1) * 100
    print(f"  BTC buy&hold за OOS-окно: {bh:+.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
