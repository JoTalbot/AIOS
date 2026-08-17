#!/usr/bin/env python3
"""R1: signal PnL simulation - does trading the emitted MM signals make money?

For each emission in data/reports/mm_signal_emitted.jsonl:
  - entry: cross the spread at emission time (UP -> buy at ask, DOWN -> sell at bid),
    stake $100;
  - exit: after H seconds (60/180) at the market (UP -> sell at bid, DOWN -> buy at ask);
  - costs: taker fee on both sides (binance spot 0.1%, configurable), spread crossing
    is inherent via bid/ask;
  - report: total PnL, winrate, profit factor, per-symbol, per-horizon.

This answers: does 63% direction accuracy on mid MOVES translate into profit after
execution costs? (Direction accuracy on moves is NOT the same as mid-return PnL.)

Usage:
    python scripts/signal_pnl_sim.py [--fee 0.001] [--stake 100] [--horizons 60 180]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")
LOG = Path("/root/AIOS/data/reports/mm_signal_emitted.jsonl")


def load_snaps(symbol: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT ts, bid, ask, mid FROM snapshots_ws WHERE symbol=? ORDER BY ts",
        (symbol,)).fetchall()
    con.close()
    return (np.array([r[0] for r in rows]), np.array([r[1] for r in rows]),
            np.array([r[2] for r in rows]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fee", type=float, default=0.001)
    ap.add_argument("--stake", type=float, default=100.0)
    ap.add_argument("--horizons", nargs="+", type=int, default=[60, 180])
    args = ap.parse_args()

    if not LOG.exists():
        print("no emissions"); return 0
    ems = [json.loads(l) for l in LOG.read_text().splitlines() if l]
    cache: dict[str, tuple] = {}
    summary: dict[str, dict] = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0,
                                                     "gross": 0.0, "fees": 0.0})

    for e in ems:
        sym = e["symbol"]
        d = e["direction"]
        if d not in ("UP", "DOWN"):
            continue
        if sym not in cache:
            cache[sym] = load_snaps(sym)
        ts, bids, asks = cache[sym]
        # entry: snapshot at/before emission time
        i0 = int(np.searchsorted(ts, e["ts"], side="right")) - 1
        if i0 < 0 or i0 >= len(ts):
            continue
        entry_px = float(asks[i0]) if d == "UP" else float(bids[i0])
        if entry_px <= 0:
            continue
        qty = args.stake / entry_px
        for H in args.horizons:
            j = int(np.searchsorted(ts, e["ts"] + H, side="left"))
            if j >= len(ts):
                continue
            exit_px = float(bids[j]) if d == "UP" else float(asks[j])
            if exit_px <= 0:
                continue
            # PnL: LONG (UP): buy@ask, sell@bid -> (exit - entry)*qty
            #      SHORT (DOWN): sell@bid, buy@ask -> (entry - exit)*qty
            direction_pnl = (exit_px - entry_px) if d == "UP" else (entry_px - exit_px)
            gross = direction_pnl * qty
            fees = args.stake * args.fee * 2  # taker both sides
            net = gross - fees
            key = f"{sym}@{H}s"
            st = summary[key]
            st["n"] += 1
            st["pnl"] += net
            st["gross"] += gross
            st["fees"] += fees
            if net > 0:
                st["wins"] += 1

    print(f"сигналов: {len(ems)} | ставка ${args.stake:.0f} | fee {args.fee:.3f} "
          f"(taker обе стороны)", flush=True)
    print(f"{'сигнал':<14} {'n':>4} {'WR':>6} {'gross $':>9} {'fees $':>8} {'net $':>9}", flush=True)
    total_n = total_wins = 0
    total_pnl = 0.0
    for key in sorted(summary):
        st = summary[key]
        wr = st["wins"] / st["n"] * 100 if st["n"] else 0
        print(f"{key:<14} {st['n']:>4} {wr:>5.0f}% {st['gross']:>+9.2f} {st['fees']:>8.2f} "
              f"{st['pnl']:>+9.2f}", flush=True)
        total_n += st["n"]
        total_wins += st["wins"]
        total_pnl += st["pnl"]
    if total_n:
        print(f"{'ИТОГО':<14} {total_n:>4} {total_wins/total_n*100:>5.0f}% "
              f"{'':>9} {'':>8} {total_pnl:>+9.2f}", flush=True)
    # per-symbol aggregate
    print("\nпо символам:", flush=True)
    by_sym: dict[str, dict] = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for e in ems:
        if e["direction"] in ("UP", "DOWN"):
            by_sym[e["symbol"]]["n"] += 1
    for k, st in summary.items():
        sym = k.split("@")[0]
        by_sym[sym]["pnl"] += st["pnl"]
    for sym in sorted(by_sym):
        print(f"  {sym}: n={by_sym[sym]['n']} net={by_sym[sym]['pnl']:+.2f}$", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
