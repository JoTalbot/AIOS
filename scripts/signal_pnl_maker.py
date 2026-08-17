#!/usr/bin/env python3
"""W4: maker-entry signal trading - limit entry at best price instead of market.

For each emission: UP -> place limit BUY at the best bid (wait for fill up to
`wait_s`), DOWN -> limit SELL at the best ask. Exit: market after H seconds from
the FILL (not from emission). Costs: maker fee on entry (0.02%), taker on exit
(0.1%). Compares to R1 (market/market, gross≈0, net -19.6$).

If maker entry fills often and the direction signal holds, this can flip the
economics (cheaper entry + better price). Honest: unfilled orders = no trade.

Usage:
    python scripts/signal_pnl_maker.py [--fee-maker 0.0002] [--fee-taker 0.001]
        [--stake 100] [--wait-s 60] [--horizon 180]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")
LOG = Path("/root/AIOS/data/reports/mm_signal_emitted.jsonl")


def load_snaps(symbol: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT ts, bid, ask FROM snapshots_ws WHERE symbol=? ORDER BY ts",
        (symbol,)).fetchall()
    con.close()
    return (np.array([r[0] for r in rows]), np.array([r[1] for r in rows]),
            np.array([r[2] for r in rows]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fee-maker", type=float, default=0.0002)
    ap.add_argument("--fee-taker", type=float, default=0.001)
    ap.add_argument("--stake", type=float, default=100.0)
    ap.add_argument("--wait-s", type=int, default=60)
    ap.add_argument("--horizon", type=int, default=180)
    args = ap.parse_args()

    if not LOG.exists():
        print("no emissions"); return 0
    ems = [json.loads(l) for l in LOG.read_text().splitlines() if l]
    cache: dict[str, tuple] = {}
    stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "filled": 0, "wins": 0,
                                                   "net": 0.0, "gross": 0.0})
    for e in ems:
        sym = e["symbol"]
        d = e["direction"]
        if d not in ("UP", "DOWN"):
            continue
        if sym not in cache:
            cache[sym] = load_snaps(sym)
        ts, bids, asks = cache[sym]
        i0 = int(np.searchsorted(ts, e["ts"], side="right")) - 1
        if i0 < 0 or i0 >= len(ts):
            continue
        # limit order at best price in the signal direction
        if d == "UP":
            lim_px = float(bids[i0])   # buy at best bid
        else:
            lim_px = float(asks[i0])   # sell at best ask
        if lim_px <= 0:
            continue
        # wait for fill: price reaches lim_px within wait_s
        j_fill = None
        for j in range(i0 + 1, len(ts)):
            if ts[j] > e["ts"] + args.wait_s:
                break
            if d == "UP" and asks[j] <= lim_px:
                j_fill = j
                break
            if d == "DOWN" and bids[j] >= lim_px:
                j_fill = j
                break
        st = stats[sym]
        st["n"] += 1
        if j_fill is None:
            continue  # no fill -> no trade
        st["filled"] += 1
        qty = args.stake / lim_px
        # exit market after horizon from FILL
        j_exit = int(np.searchsorted(ts, ts[j_fill] + args.horizon, side="left"))
        if j_exit >= len(ts):
            continue
        exit_px = float(bids[j_exit]) if d == "UP" else float(asks[j_exit])
        if exit_px <= 0:
            continue
        gross = ((exit_px - lim_px) if d == "UP" else (lim_px - exit_px)) * qty
        fees = args.stake * args.fee_maker + args.stake * args.fee_taker
        net = gross - fees
        st["gross"] += gross
        st["net"] += net
        if net > 0:
            st["wins"] += 1

    print(f"сигналов: {len(ems)} | maker-вход (wait {args.wait_s}s), taker-выход "
          f"({args.horizon}s) | stake ${args.stake:.0f}", flush=True)
    print(f"{'символ':<8} {'сигн':>4} {'филлы':>5} {'fill%':>6} {'WR':>5} "
          f"{'gross $':>8} {'net $':>8}", flush=True)
    tn = tf = tw = 0
    tnet = tgross = 0.0
    for sym in sorted(stats):
        st = stats[sym]
        fill_pct = st["filled"] / st["n"] * 100 if st["n"] else 0
        wr = st["wins"] / st["filled"] * 100 if st["filled"] else 0
        print(f"{sym:<8} {st['n']:>4} {st['filled']:>5} {fill_pct:>5.0f}% {wr:>4.0f}% "
              f"{st['gross']:>+8.2f} {st['net']:>+8.2f}", flush=True)
        tn += st["n"]; tf += st["filled"]; tw += st["wins"]
        tnet += st["net"]; tgross += st["gross"]
    if tf:
        print(f"{'ИТОГО':<8} {tn:>4} {tf:>5} {tf/tn*100:>5.0f}% {tw/tf*100:>4.0f}% "
              f"{tgross:>+8.2f} {tnet:>+8.2f}", flush=True)
    print(f"\nСравнение с R1 (market/market): net был -19.61$ на 98 сделках.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
