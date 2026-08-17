#!/usr/bin/env python3
"""Partial take-profit variants + bootstrap significance for the N1 (trail=1.0) finding.

Reuses the fold-0.70 OOS setup from scripts/quant_oos_robustness.py (fresh CatBoost v2
on the 70% train segment, allowlist prices, ML>=0.65 fixed threshold, $200/leg).

1. Variants (a-priori):
   - BASE: trail 0.988 (prod legacy)
   - N1:   trail 1.0 (hard trail)
   - PT1:  close 50% at +1.0%, remainder on hard trail (1.0) + TP2%/SL1%
   - PT2:  close 50% at +1.5%, remainder on hard trail (1.0) + TP2%/SL1%
   - PT3:  close 50% at +1.0%, remainder on soft trail (0.995) + TP2%/SL1%

2. Bootstrap over symbols (2000 resamples with replacement) for BASE vs N1:
   90% percentile interval of per-sample PnL and share of positive samples.

Usage:
    python scripts/quant_oos_partial_tp_bootstrap.py [--output data/reports/oos_partial_tp_bootstrap.md]
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

import quant_monthly_backtest as qmb
from quant_oos_robustness import (
    BASE_V,
    N1_V,
    load_series,
    predict_all,
    train_fold,
)

STAKE = 200.0
FEE = qmb.PROFILE["fee_rate"]
COST = qmb.PROFILE["half_spread_rate"] + qmb.PROFILE["slippage_rate"]
TRAIN_FRAC = 0.70

PT_VARIANTS = {
    "PT1: 50%@+1.0%, остаток trail 1.0": {"stage1_pct": 0.010, "stage1_frac": 0.5, "rem_trail": 1.0},
    "PT2: 50%@+1.5%, остаток trail 1.0": {"stage1_pct": 0.015, "stage1_frac": 0.5, "rem_trail": 1.0},
    "PT3: 50%@+1.0%, остаток trail 0.995": {"stage1_pct": 0.010, "stage1_frac": 0.5, "rem_trail": 0.995},
}


def simulate_partial(sym: str, s: dict, test_start: int, variant: dict) -> list[dict]:
    """Two-stage exit: close stage1_frac at stage1_pct, remainder on rem_trail + TP/SL."""
    closes, highs, lows = s["closes"], s["highs"], s["lows"]
    times, probs = s["times"], s["probs"]
    tp = qmb.PROFILE["take_profit_pct"]
    sl = qmb.PROFILE["stop_loss_pct"]
    stage1_pct = variant["stage1_pct"]
    stage1_frac = variant["stage1_frac"]
    rem_trail = variant["rem_trail"]

    history: list[float] = [float(c) for c in closes[:test_start]]
    pos = None
    trades: list[dict] = []
    last_ts = 0

    for k in range(test_start, len(closes)):
        price = float(closes[k])
        ts = int(times[k])
        ml_prob = float(probs[k]) if k < len(probs) and not np.isnan(float(probs[k])) else None
        history.append(price)

        if pos is not None:
            entry_mid = pos["entry_mid"]
            qty = pos["qty"]
            invested = pos["invested"]
            max_seen = max(pos["max_seen"], price)
            pos["max_seen"] = max_seen
            hi, lo = float(highs[k]), float(lows[k])
            # stage 1: partial close once
            if not pos.get("staged") and hi >= entry_mid * (1.0 + stage1_pct):
                close_qty = qty * stage1_frac
                exit_px = entry_mid * (1.0 + stage1_pct) * (1.0 - COST)
                proceeds = exit_px * close_qty
                net1 = proceeds - invested * stage1_frac - exit_px * close_qty * FEE
                pos["qty"] = qty - close_qty
                pos["invested"] = invested * (1.0 - stage1_frac)
                pos["staged"] = True
                pos["stage1_net"] = net1
                pos["stage1_ts"] = ts
                pos["stage1_entry_mid"] = entry_mid
            exit_px = None
            reason = ""
            if lo <= entry_mid * (1.0 + sl):
                exit_px = entry_mid * (1.0 + sl) * (1.0 - COST)
                reason = "stop_loss"
            elif hi >= entry_mid * (1.0 + tp):
                exit_px = entry_mid * (1.0 + tp) * (1.0 - COST)
                reason = "take_profit"
            elif pos.get("staged") and max_seen > entry_mid * 1.01 and lo <= max_seen * rem_trail:
                exit_px = max_seen * rem_trail * (1.0 - COST)
                reason = "trailing_stop"
            if exit_px is not None and pos["qty"] > 1e-12:
                proceeds = exit_px * pos["qty"]
                net2 = proceeds - pos["invested"] - exit_px * pos["qty"] * FEE
                total_net = pos.get("stage1_net", 0.0) + net2
                trades.append({"symbol": sym, "net": total_net,
                               "pct": total_net / invested * 100.0 if invested else 0.0,
                               "reason": f"{'partial+' if pos.get('stage1_net') else ''}{reason}",
                               "opened_at": pos["opened_at"], "ts": ts})
                pos = None

        # entry
        an = qmb.record_and_analyze(history, ml_prob, 0.0 if sym in qmb.RL_ASSETS else None)
        if an["signal"] != "BUY_LONG" or an["confidence"] < qmb.PROFILE["min_confidence"]:
            continue
        if ml_prob is None or ml_prob < 0.65:
            continue
        rl = 0.0 if sym in qmb.RL_ASSETS else None
        if rl is not None and rl <= qmb.PROFILE["rl_veto_position"]:
            continue
        entry_fee = STAKE * FEE
        exec_px = price * (1.0 + COST)
        pos = {"entry_mid": price, "qty": (STAKE - entry_fee) / exec_px,
               "invested": STAKE, "max_seen": price, "opened_at": ts}

    if pos is not None:  # mark-to-market
        exit_px = price * (1.0 - COST)
        proceeds = exit_px * pos["qty"]
        net2 = proceeds - pos["invested"] - exit_px * pos["qty"] * FEE
        total_net = pos.get("stage1_net", 0.0) + net2
        trades.append({"symbol": sym, "net": total_net,
                       "pct": total_net / pos.get("stage1_entry_mid", price) * 0.0,
                       "reason": "period_end", "opened_at": pos["opened_at"], "ts": ts})
    return trades


def unique_trades(trades: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out = []
    for t in trades:
        key = (t["symbol"], t["opened_at"])
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def pnl_of(trades: list[dict]) -> float:
    return sum(t["net"] for t in unique_trades(trades))


def metrics(trades: list[dict]) -> dict:
    tr = unique_trades(trades)
    if not tr:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "pnl": 0.0, "avg": 0.0}
    wins = [t for t in tr if t["net"] > 0]
    gw = sum(t["net"] for t in wins)
    gl = -sum(t["net"] for t in tr if t["net"] < 0)
    return {"n": len(tr), "wr": len(wins) / len(tr) * 100.0,
            "pf": gw / gl if gl > 0 else float("inf"),
            "pnl": sum(t["net"] for t in tr),
            "avg": statistics.mean(t["pct"] for t in tr)}


def bootstrap_symbols(by_symbol: dict[str, list[dict]], n_iter: int = 2000, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    symbols = list(by_symbol)
    diffs = []
    base_pnls = []
    n1_pnls = []
    for _ in range(n_iter):
        pick = rng.choice(symbols, size=len(symbols), replace=True)
        b = sum(pnl_of(by_symbol[sym].get("BASE", [])) for sym in pick)
        n1 = sum(pnl_of(by_symbol[sym].get("N1", [])) for sym in pick)
        base_pnls.append(b)
        n1_pnls.append(n1)
        diffs.append(n1 - b)
    lo_b, hi_b = np.percentile(base_pnls, [5, 95])
    lo_n, hi_n = np.percentile(n1_pnls, [5, 95])
    lo_d, hi_d = np.percentile(diffs, [5, 95])
    return {
        "n_iter": n_iter,
        "base": {"lo": lo_b, "hi": hi_b, "pos_share": float(np.mean(np.array(base_pnls) > 0))},
        "n1": {"lo": lo_n, "hi": hi_n, "pos_share": float(np.mean(np.array(n1_pnls) > 0))},
        "diff": {"lo": lo_d, "hi": hi_d, "pos_share": float(np.mean(np.array(diffs) > 0))},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=Path("data/reports/oos_partial_tp_bootstrap.md"))
    args = ap.parse_args()

    series = load_series("allowlist")
    print(f"symbols: {len(series)}", flush=True)
    model = train_fold(series, TRAIN_FRAC)
    series = predict_all(series, model, TRAIN_FRAC)

    cuts = {sym: int(len(s["df"]) * TRAIN_FRAC) for sym, s in series.items()}

    results: dict[str, list[dict]] = {}
    by_symbol: dict[str, dict[str, list[dict]]] = {sym: {} for sym in series}
    for name, v in (("BASE", BASE_V), ("N1", N1_V)):
        trades = []
        for sym, s in series.items():
            tt = __import__("quant_oos_profit_experiments").simulate(
                sym, s, v, cuts[sym], 0.65)
            trades.extend(tt)
            by_symbol[sym][name] = tt
        results[name] = trades
        m = metrics(trades)
        print(f"{name}: n={m['n']} wr={m['wr']:.1f}% PF={m['pf']:.2f} pnl={m['pnl']:+.2f}$", flush=True)

    for name, v in PT_VARIANTS.items():
        trades = []
        for sym, s in series.items():
            trades.extend(simulate_partial(sym, s, cuts[sym], v))
        results[name] = trades
        m = metrics(trades)
        print(f"{name}: n={m['n']} wr={m['wr']:.1f}% PF={m['pf']:.2f} pnl={m['pnl']:+.2f}$", flush=True)

    bs = bootstrap_symbols(by_symbol)
    print(f"bootstrap: N1 90% CI [{bs['n1']['lo']:+.2f}, {bs['n1']['hi']:+.2f}] "
          f"pos_share={bs['n1']['pos_share']:.1%}; "
          f"diff CI [{bs['diff']['lo']:+.2f}, {bs['diff']['hi']:+.2f}] "
          f"pos_share={bs['diff']['pos_share']:.1%}", flush=True)

    md = ["# Частичный тейк + бутстрэп N1 (OOS fold 0.70)", "",
          "Окно: test-хвост 30% истории (allowlist), свежая CatBoost v2, ML>=0.65, $200/сделку.",
          "",
          "| Вариант | Сделок | Winrate | PF | PnL $ | avg % |",
          "|---|---:|---:|---:|---:|---:|"]
    for name in list(results):
        m = metrics(results[name])
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        md.append(f"| {name} | {m['n']} | {m['wr']:.1f}% | {pf} | {m['pnl']:+.2f} | {m['avg']:+.3f} |")
    md += ["",
           "## Бутстрэп по символам (2000 ресемплов с повторением)",
           "",
           "| Метрика | BASE | N1 | Δ (N1-BASE) |",
           "|---|---:|---:|---:|",
           f"| 90% CI PnL $ | [{bs['base']['lo']:+.2f}, {bs['base']['hi']:+.2f}] | "
           f"[{bs['n1']['lo']:+.2f}, {bs['n1']['hi']:+.2f}] | "
           f"[{bs['diff']['lo']:+.2f}, {bs['diff']['hi']:+.2f}] |",
           f"| Доля положительных выборок | {bs['base']['pos_share']:.1%} | "
           f"{bs['n1']['pos_share']:.1%} | {bs['diff']['pos_share']:.1%} |"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
