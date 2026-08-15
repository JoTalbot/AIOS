#!/usr/bin/env python3
"""WebSocket orderbook depth collector for market-making research (stage 3).

Subscribes to Binance public partial-depth streams (wss://stream.binance.com:9443,
btcusdt@depth20@100ms) for a set of pairs, keeps the freshest snapshot per second
and appends it to data/quant/orderbooks.sqlite table `snapshots_ws`
(same schema as `snapshots`, plus a source tag). Read-only market data; never
authenticates or trades.

Usage:
    python scripts/collect_orderbook_ws.py [--pairs BTC ETH SOL] [--interval 1.0]
        [--db data/quant/orderbooks.sqlite]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import time
from pathlib import Path

import websockets

BASE_WS = "wss://stream.binance.com:9443/ws"


class WSStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS snapshots_ws (
            ts REAL NOT NULL, source TEXT NOT NULL, symbol TEXT NOT NULL,
            bid REAL NOT NULL, ask REAL NOT NULL, mid REAL NOT NULL, spread_bps REAL NOT NULL,
            bid_depth_usd REAL NOT NULL, ask_depth_usd REAL NOT NULL,
            bids_json TEXT NOT NULL, asks_json TEXT NOT NULL, latency_ms REAL NOT NULL
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_ws_sym_ts ON snapshots_ws(symbol, ts)")

    def add_batch(self, rows: list[tuple]):
        if not rows:
            return
        self.db.executemany(
            "INSERT INTO snapshots_ws VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        self.db.commit()


def depth_to_json(levels) -> str:
    return json.dumps([[float(l[0]), float(l[1])] for l in levels])


def level_depth_usd(levels, mid: float) -> float:
    return sum(float(l[0]) * float(l[1]) for l in levels)


async def consume_one(ws, pair: str, interval: float, store: WSStore,
                     source: str = "binance_ws") -> None:
    """One connection per pair: recv its own stream, flush freshest per interval."""
    latest: dict | None = None
    last_ts = 0.0
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("lastUpdateId") is None:
            continue
        bids, asks = msg.get("bids", []), msg.get("asks", [])
        if not bids or not asks:
            continue
        bid = float(bids[0][0])
        ask = float(asks[0][0])
        if bid <= 0 or ask <= 0 or ask <= bid:
            continue
        mid = (bid + ask) / 2.0
        latest = {
            "ts": time.time(),
            "bid": bid, "ask": ask, "mid": mid,
            "spread_bps": (ask - bid) / mid * 1e4,
            "bid_depth_usd": level_depth_usd(bids, mid),
            "ask_depth_usd": level_depth_usd(asks, mid),
            "bids_json": depth_to_json(bids),
            "asks_json": depth_to_json(asks),
            "latency_ms": 0.0,
        }
        now = time.time()
        if latest and (now - last_ts) >= interval:
            r = latest
            store.add_batch([(r["ts"], source, pair, r["bid"], r["ask"], r["mid"],
                              r["spread_bps"], r["bid_depth_usd"], r["ask_depth_usd"],
                              r["bids_json"], r["asks_json"], r["latency_ms"])])
            last_ts = now
            latest = None


async def keepalive(ws, interval: float = 20.0) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await ws.ping()
        except Exception:
            return


async def run_one(pair: str, interval: float, db_path: Path) -> None:
    store = WSStore(db_path)
    url = f"{BASE_WS}/{pair.lower()}usdt@depth20@100ms"
    while True:
        try:
            async with websockets.connect(url, ping_interval=None) as ws:
                print(f"connected {pair}", flush=True)
                await asyncio.gather(consume_one(ws, pair, interval, store),
                                     keepalive(ws))
        except Exception as e:
            print(f"{pair} error: {e}; reconnect in 5s", flush=True)
            await asyncio.sleep(5)


async def run(pairs: list[str], interval: float, db_path: Path) -> None:
    await asyncio.gather(*(run_one(p, interval, db_path) for p in pairs))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", nargs="+", default=["BTC", "ETH", "SOL"])
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--db", type=Path, default=Path("/root/AIOS/data/quant/orderbooks.sqlite"))
    args = ap.parse_args()
    try:
        asyncio.run(run(args.pairs, args.interval, args.db))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
