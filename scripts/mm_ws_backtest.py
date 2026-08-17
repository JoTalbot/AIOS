#!/usr/bin/env python3
"""Interim MM evaluation on the ws snapshot stream (read-only research).

Loads snapshots_ws (1Hz stream, 19 symbols; BTC/ETH additionally have a full
100ms stream which is decimated to ~1Hz here for comparability), replays the
same passive-maker logic as scripts/mm_proto_backtest.py (naive vs gated,
optional queue model), and prints per-symbol latency statistics.

This is a RESEARCH prototype, not live trading.

Usage:
    python scripts/mm_ws_backtest.py --symbol BTC [--mode naive|gated] [--queue-model]
        [--min-interval 0.9] [--half-spread-bps 2] [--max-size-usd 2000]
        [--inv-cap-usd 10000] [--symbols BTC,ETH,SOL]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.mm_proto_backtest import run_mm  # noqa: E402

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")

# Fee model stored in log (16.08): taker 0.0005 spot baseline; maker 0.0002 used in W1.
FEE = 0.0005


def _decimate(rows: list[tuple], min_interval: float) -> list[tuple]:
    """Keep the first row of each min_interval bucket (pure, unit-tested)."""

    out: list[tuple] = []
    last_ts = -1e18
    for r in rows:
        ts = float(r[0])
        if ts - last_ts < min_interval:
            continue
        last_ts = ts
        out.append(r)
    return out


def load_ws(symbol: str, min_interval: float = 0.9) -> list[dict]:
    con = sqlite3.connect(DB, timeout=30)
    cur = con.execute(
        "SELECT ts, bid, ask, mid, spread_bps, bid_depth_usd, ask_depth_usd, "
        "bids_json, asks_json, latency_ms FROM snapshots_ws WHERE symbol=? "
        "ORDER BY ts", (symbol,))
    out = []
    for r in _decimate(cur.fetchall(), min_interval):
        out.append({"ts": r[0], "bid": r[1], "ask": r[2], "mid": r[3],
                    "spread_bps": r[4], "bid_depth_usd": r[5], "ask_depth_usd": r[6],
                    "bids": json.loads(r[7]) if r[7] else [],
                    "asks": json.loads(r[8]) if r[8] else [],
                    "latency_ms": r[9]})
    con.close()
    return out


def latency_stats(snaps: list[dict]) -> dict:
    lats = [s["latency_ms"] for s in snaps if s["latency_ms"] > 0]
    if not lats:
        return {"n": 0}
    lats.sort()
    return {
        "n": len(lats),
        "share_pct": round(100.0 * len(lats) / len(snaps), 1),
        "median_ms": round(statistics.median(lats), 1),
        "p90_ms": round(lats[int(len(lats) * 0.90)], 1),
        "p99_ms": round(lats[int(len(lats) * 0.99)], 1),
        "max_ms": round(lats[-1], 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbols", default="BTC,ETH,SOL,BNB,NEAR,ADA,LINK,XRP")
    ap.add_argument("--min-interval", type=float, default=0.9)
    ap.add_argument("--mode", default="naive", choices=["naive", "gated"])
    ap.add_argument("--queue-model", action="store_true")
    ap.add_argument("--half-spread-bps", type=float, default=2.0)
    ap.add_argument("--max-size-usd", type=float, default=2000.0)
    ap.add_argument("--inv-cap-usd", type=float, default=10000.0)
    args = ap.parse_args()

    results = {}
    for symbol in args.symbols.split(","):
        symbol = symbol.strip()
        snaps = load_ws(symbol, args.min_interval)
        if len(snaps) < 500:
            print(f"{symbol}: not enough data ({len(snaps)})", flush=True)
            continue
        res = run_mm(snaps, mode=args.mode, half_spread_bps=args.half_spread_bps,
                     max_size_usd=args.max_size_usd, inv_cap_usd=args.inv_cap_usd,
                     fee_rate=FEE, hold_snaps=1, queue_model=args.queue_model)
        res["snapshots"] = len(snaps)
        res["latency"] = latency_stats(snaps)
        results[symbol] = res
        print(f"{symbol}: {json.dumps(res)}", flush=True)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
