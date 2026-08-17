#!/usr/bin/env python3
"""SHORT-direction experiment on OOS (mirror of the LONG engine).

The engine generates SELL_SHORT signals and ml_prob<=0.40 (prob_down>60%) but
entries are LONG-only. In a bear market (the entire 2026 OOS window was below
SMA200) this leaves the most probable direction untraded. This script simulates
mirrored SHORT entries with the same cost model and compares LONG-only vs
LONG+SHORT vs SHORT-only on the fold-0.70 OOS window (fresh CatBoost v2 on train).

Mirror rules:
- entry: SELL_SHORT signal, confidence>=0.88, ml_prob<=0.40, free profile.
- exit: SL when price rises abs(sl) (loss), TP when price falls tp (profit),
  trailing: after -1% favorable move, exit when price bounces back from min_seen.
- costs applied symmetrically.

Usage:
    python scripts/quant_oos_short_experiment.py [--output data/reports/oos_short_experiment.md]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quant_monthly_backtest as qmb
from quant_oos_robustness import load_series, predict_all, train_fold

STAKE = 200.0
FEE = qmb.PROFILE["fee_rate"]
COST = qmb.PROFILE["half_spread_rate"] + qmb.PROFILE["slippage_rate"]
TRAIN_FRAC = 0.70
TP = qmb.PROFILE["take_profit_pct"]      # 0.02
SL = abs(qmb.PROFILE["stop_loss_pct"])   # 0.01
TRAIL = 1.0  # hard trail (winner from LONG experiments)


def simulate_short(sym: str, s: dict, test_start: int, ml_max: float = 0.40) -> list[dict]:
    """Mirrored SHORT simulation; same entry gate shape as the LONG engine."""
    closes, highs, lows = s["closes"], s["highs"], s["lows"]
    times, probs = s["times"], s["probs"]
    history: list[float] = [float(c) for c in closes[:test_start]]
    pos = None
    trades: list[dict] = []

    for k in range(test_start, len(closes)):
        price = float(closes[k])
        ts = int(times[k])
        ml_prob = float(probs[k]) if k < len(probs) and not np.isnan(float(probs[k])) else None
        history.append(price)

        if pos is not None:
            entry_mid = pos["entry_mid"]
            qty = pos["qty"]
            min_seen = min(pos["min_seen"], price)
            pos["min_seen"] = min_seen
            hi, lo = float(highs[k]), float(lows[k])
            exit_px = None
            reason = ""
            # SL: price rises against the short
            if hi >= entry_mid * (1.0 + SL):
                exit_px = entry_mid * (1.0 + SL) * (1.0 + COST)
                reason = "stop_loss"
            # TP: price falls in favor
            elif lo <= entry_mid * (1.0 - TP):
                exit_px = entry_mid * (1.0 - TP) * (1.0 + COST)
                reason = "take_profit"
            # hard trailing: after -1% favorable, exit on bounce from min_seen
            elif min_seen < entry_mid * 0.99 and hi >= min_seen * (2.0 - TRAIL):
                exit_px = min_seen * (2.0 - TRAIL) * (1.0 + COST)
                reason = "trailing_stop"
            if exit_px is not None:
                proceeds = exit_px * qty
                net = pos["invested"] - proceeds - exit_px * qty * FEE
                trades.append({"symbol": sym, "net": net, "pct": net / pos["invested"] * 100.0,
                               "reason": reason, "opened_at": pos["opened_at"], "ts": ts})
                pos = None

        # entry: SELL_SHORT mirror
        an = qmb.record_and_analyze(history, ml_prob, 0.0 if sym in qmb.RL_ASSETS else None)
        if an["signal"] != "SELL_SHORT" or an["confidence"] < qmb.PROFILE["min_confidence"]:
            continue
        if ml_prob is None or ml_prob > ml_max:
            continue
        entry_fee = STAKE * FEE
        exec_px = price * (1.0 - COST)  # short sells at bid
        pos = {"entry_mid": price, "qty": (STAKE - entry_fee) / exec_px,
               "invested": STAKE, "min_seen": price, "opened_at": ts}

    if pos is not None:  # mark-to-market
        exit_px = price * (1.0 + COST)
        proceeds = exit_px * pos["qty"]
        net = pos["invested"] - proceeds - exit_px * pos["qty"] * FEE
        trades.append({"symbol": sym, "net": net, "pct": net / STAKE * 100.0,
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=Path("data/reports/oos_short_experiment.md"))
    args = ap.parse_args()

    series = load_series("allowlist")
    print(f"symbols: {len(series)}", flush=True)
    model = train_fold(series, TRAIN_FRAC)
    series = predict_all(series, model, TRAIN_FRAC)
    cuts = {sym: int(len(s["df"]) * TRAIN_FRAC) for sym, s in series.items()}

    from quant_oos_profit_experiments import simulate  # LONG engine reuse

    long_trades, short_trades = [], []
    for sym, s in series.items():
        long_trades.extend(simulate(sym, s, {"trail": TRAIL}, cuts[sym], 0.65))
        short_trades.extend(simulate_short(sym, s, cuts[sym], 0.40))

    for ml_max in (0.35, 0.40):
        st = []
        for sym, s in series.items():
            st.extend(simulate_short(sym, s, cuts[sym], ml_max))
        m = metrics(st)
        print(f"SHORT ml<={ml_max}: n={m['n']} wr={m['wr']:.1f}% PF={m['pf']:.2f} "
              f"pnl={m['pnl']:+.2f}$", flush=True)
        if ml_max == 0.40:
            short_trades = st

    lm, sm = metrics(long_trades), metrics(short_trades)
    comb = unique_trades(long_trades + short_trades)
    cm = metrics(comb)
    print(f"LONG:  n={lm['n']} wr={lm['wr']:.1f}% PF={lm['pf']:.2f} pnl={lm['pnl']:+.2f}$", flush=True)
    print(f"SHORT: n={sm['n']} wr={sm['wr']:.1f}% PF={sm['pf']:.2f} pnl={sm['pnl']:+.2f}$", flush=True)
    print(f"LONG+SHORT: n={cm['n']} wr={cm['wr']:.1f}% PF={cm['pf']:.2f} pnl={cm['pnl']:+.2f}$", flush=True)

    t0 = min(int(s["times"][cuts[sym]]) for sym, s in series.items())
    d0 = datetime.fromtimestamp(t0 / 1000, tz=UTC).strftime("%Y-%m-%d")
    md = ["# SHORT-эксперимент (зеркало LONG) на OOS", "",
          f"Окно: {d0} .. сегодня, fold 0.70, свежая CatBoost v2, $200/сделку, "
          "жёсткий трейлинг (trail=1.0).",
          "",
          "| Стратегия | Сделок | Winrate | PF | PnL $ | avg % |",
          "|---|---:|---:|---:|---:|---:|"]
    for name, m in (("LONG-only (текущая)", lm), ("SHORT-only (ml<=0.40)", sm),
                    ("LONG+SHORT (комбо)", cm)):
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        md.append(f"| {name} | {m['n']} | {m['wr']:.1f}% | {pf} | {m['pnl']:+.2f} | {m['avg']:+.3f} |")
    md += ["", "## Сделки SHORT (ml<=0.40)", ""]
    for t in sorted(unique_trades(short_trades), key=lambda x: x["opened_at"]):
        d = datetime.fromtimestamp(t["opened_at"] / 1000, tz=UTC).strftime("%m-%d %H:%M")
        md.append(f"- {d} {t['symbol']}: {t['net']:+.2f}$ ({t['pct']:+.2f}%) — {t['reason']}")
    if not unique_trades(short_trades):
        md.append("- нет сделок")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
