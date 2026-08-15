#!/usr/bin/env python3
"""Winrate experiment battery over the yearly backtest harness (read-only, in-sample).

Reuses 1:1 signal/feature functions from scripts/quant_monthly_backtest.py.
Free profile per symbol (identical to --free-profile trades, verified vs BASE).
Variants: trend gates, ML threshold, exit grid, donor blacklist.

Usage:
    python scripts/quant_winrate_experiments.py [--months 12] [--output data/reports/winrate_experiments_1y.md]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from datetime import UTC

import quant_monthly_backtest as qmb

STAKE = 200.0
FEE = qmb.PROFILE["fee_rate"]
COST = qmb.PROFILE["half_spread_rate"] + qmb.PROFILE["slippage_rate"]


def simulate(sym: str, s: dict, variant: dict) -> list[dict]:
    """Per-symbol free-profile simulation; mirrors qmb exits 1:1."""
    closes, highs, lows = s["closes"], s["highs"], s["lows"]
    times, probs = s["times"], s["probs"]
    i0 = s["i0"]
    ml_min = variant.get("ml_min", qmb.PROFILE["ml_min_prob_up"])
    tp = variant.get("tp", qmb.PROFILE["take_profit_pct"])
    sl = variant.get("sl", qmb.PROFILE["stop_loss_pct"])
    trail = variant.get("trail", qmb.PROFILE["trail_ratio"])
    trend = variant.get("trend")  # None | "asset" | "btc"
    history: list[float] = [float(c) for c in closes[:i0]]

    pos = None
    trades: list[dict] = []
    for k in range(i0, len(closes)):
        price = float(closes[k])
        ts = int(times[k])
        ml_prob = float(probs[k]) if k < len(probs) and not np.isnan(float(probs[k])) else None
        history.append(price)

        if pos is not None:
            entry_mid = pos["entry_mid"]
            qty = pos["qty"]
            max_seen = max(pos["max_seen"], price)
            pos["max_seen"] = max_seen
            hi, lo = float(highs[k]), float(lows[k])
            exit_px = None
            reason = ""
            if lo <= entry_mid * (1.0 + sl):
                exit_px = entry_mid * (1.0 + sl) * (1.0 - COST)
                reason = "stop_loss"
            elif hi >= entry_mid * (1.0 + tp):
                exit_px = entry_mid * (1.0 + tp) * (1.0 - COST)
                reason = "take_profit"
            elif max_seen > entry_mid * 1.01 and lo <= max_seen * trail:
                exit_px = max_seen * trail * (1.0 - COST)
                reason = "trailing_stop"
            else:
                an = qmb.record_and_analyze(history, ml_prob, 0.0 if sym in qmb.RL_ASSETS else None)
                if (an["signal"] == "SELL_SHORT" and an["confidence"] >= qmb.PROFILE["min_confidence"]
                        and ml_prob is not None and ml_prob <= 0.40
                        and (ts - pos["opened_at"]) >= qmb.PROFILE["min_hold_seconds"] * 1000):
                    exit_px = price * (1.0 - COST)
                    reason = "confirmed_bearish_exit"
            if exit_px is not None:
                proceeds = exit_px * qty
                net = proceeds - pos["invested"] - exit_px * qty * FEE  # entry_fee уже в qty
                trades.append({"symbol": sym, "net": net,
                               "pct": net / pos["invested"] * 100.0, "reason": reason})
                pos = None

        if trend == "asset" and s["sma200"][k] and not (price > s["sma200"][k]):
            continue
        if trend == "btc" and s["btc_up"].get(ts) is False:
            continue
        an = qmb.record_and_analyze(history, ml_prob, 0.0 if sym in qmb.RL_ASSETS else None)
        if an["signal"] != "BUY_LONG" or an["confidence"] < qmb.PROFILE["min_confidence"]:
            continue
        if ml_prob is None or ml_prob < ml_min:
            continue
        rl = 0.0 if sym in qmb.RL_ASSETS else None
        if rl is not None and rl <= qmb.PROFILE["rl_veto_position"]:
            continue
        entry_fee = STAKE * FEE
        exec_px = price * (1.0 + COST)
        pos = {"entry_mid": price, "qty": (STAKE - entry_fee) / exec_px,
               "invested": STAKE, "entry_fee": entry_fee, "max_seen": price, "opened_at": ts}

    if pos is not None:  # mark-to-market at period end
        exit_px = price * (1.0 - COST)
        proceeds = exit_px * pos["qty"]
        net = proceeds - pos["invested"] - exit_px * pos["qty"] * FEE  # entry_fee уже в qty
        trades.append({"symbol": sym, "net": net, "pct": net / STAKE * 100.0, "reason": "period_end"})
    return trades


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "pnl": 0.0, "avg": 0.0}
    wins = [t for t in trades if t["net"] > 0]
    gw = sum(t["net"] for t in wins)
    gl = -sum(t["net"] for t in trades if t["net"] < 0)
    return {"n": len(trades), "wr": len(wins) / len(trades) * 100.0,
            "pf": gw / gl if gl > 0 else float("inf"),
            "pnl": sum(t["net"] for t in trades),
            "avg": statistics.mean(t["pct"] for t in trades)}


VARIANTS = [
    ("BASE: текущая (ML>=0.65)", {}),
    ("T1: тренд-гейт asset>SMA200", {"trend": "asset"}),
    ("T2: тренд-гейт рынка (BTC>SMA200)", {"trend": "btc"}),
    ("M1: ML>=0.70", {"ml_min": 0.70}),
    ("M2: ML>=0.75", {"ml_min": 0.75}),
    ("X1: TP+1.0%/SL-1.0%", {"tp": 0.010, "sl": -0.010}),
    ("X2: TP+1.2%/SL-0.8%", {"tp": 0.012, "sl": -0.008}),
    ("X3: TP+3.0%/SL-1.5%", {"tp": 0.030, "sl": -0.015}),
    ("B1: блэклист доноров (SEI,OP,KAS,UNI)", {"blacklist": {"SEI", "OP", "KAS", "UNI"}}),
    ("C1: T1 + ML>=0.70", {"trend": "asset", "ml_min": 0.70}),
    ("C2: T1 + ML0.70 + B1", {"trend": "asset", "ml_min": 0.70,
                              "blacklist": {"SEI", "OP", "KAS", "UNI"}}),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--output", type=Path, default=Path("data/reports/winrate_experiments_1y.md"))
    args = ap.parse_args()

    from datetime import datetime

    from catboost import CatBoostClassifier
    from dateutil.relativedelta import relativedelta

    symbols, _venue_used = qmb.load_symbols("allowlist")
    print(f"symbols: {len(symbols)}", flush=True)
    model = CatBoostClassifier()
    model.load_model(str(qmb.MODELS_DIR / "catboost_price_dir_v2.cbm"))

    last_ts = max(int(df["timestamp_ms"].iloc[-1]) for df in symbols.values())
    start_ms = int((datetime.fromtimestamp(last_ts / 1000, tz=UTC)
                    - relativedelta(months=args.months)).timestamp() * 1000)

    series: dict[str, dict] = {}
    for sym, df in symbols.items():
        feats = qmb._compute_features(df)
        X = feats[qmb.FEATURES].values.astype(np.float64)
        probs = model.predict_proba(X)[:, 1] if len(X) else np.array([])
        idx = np.where(df["timestamp_ms"].values >= start_ms)[0]
        if len(idx) < 100:
            continue
        series[sym] = {
            "closes": df["close"].values, "highs": df["high"].values, "lows": df["low"].values,
            "times": df["timestamp_ms"].values, "probs": probs, "i0": int(idx[0]),
            "sma200": df["close"].rolling(200).mean().values,
            "btc_up": {},
        }

    # BTC market-regime map (close > SMA200 by timestamp)
    btc = series.get("BTC")
    if btc:
        by_ts = {int(t): k for k, t in enumerate(btc["times"])}
        for ts, k in by_ts.items():
            sma = btc["sma200"][k]
            btc["btc_up"][ts] = bool(sma == sma and btc["closes"][k] > sma)
    for sym, s in series.items():
        if sym != "BTC":
            s["btc_up"] = btc["btc_up"] if btc else {}

    print(f"series ready: {len(series)}; running {len(VARIANTS)} variants...", flush=True)
    rows = []
    for name, variant in VARIANTS:
        bl = variant.get("blacklist", set())
        trades = []
        for sym, s in series.items():
            if sym in bl:
                continue
            trades.extend(simulate(sym, s, variant))
        m = metrics(trades)
        rows.append((name, m))
        print(f"{name}: n={m['n']} wr={m['wr']:.1f}% PF={m['pf']:.2f} pnl={m['pnl']:+.2f}$", flush=True)

    base = rows[0][1]
    md = ["# Эксперименты по поднятию винрейта (1 год, in-sample)", "",
          f"Период: последние {args.months} мес. | Цены: allowlist (kucoin/bitstamp) | "
          f"Ставка фикс ${STAKE:.0f}/сделку | Профиль: свободный (без kill-switch)", "",
          "| Вариант | Сделок | Winrate | PF | PnL $ | Δ к базе $ |", "|---|---:|---:|---:|---:|---:|"]
    for name, m in rows:
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        md.append(f"| {name} | {m['n']} | {m['wr']:.1f}% | {pf} | {m['pnl']:+.2f} | "
                  f"{m['pnl'] - base['pnl']:+.2f} |")
    md += ["", "**Важно:** все результаты in-sample (тот же год, что обучение ML и подбор параметров). "
               "Победитель сетки обязан пройти свежий OOS walk-forward перед любым выводом о проде."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
