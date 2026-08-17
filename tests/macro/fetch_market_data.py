#!/usr/bin/env python3
"""Macro + on-chain data collector (Yahoo Finance + blockchain.info).

Collects daily series into data/market_data/{name}.jsonl:
  - DXY, SPX, NDX, BTC_USD, IBIT  (Yahoo Finance close prices)
  - hashrate, n_tx, n_unique_addr, tx_vol_usd, mempool  (blockchain.info)
Transport is injectable (for tests); real run uses urllib.

Usage:
    python fetch_market_data.py [--out-dir data/market_data] [--days 400]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range={}d&interval=1d"
BLOCKCHAIN = "https://api.blockchain.info/charts/{}?timespan={}days&format=json"

YAHOO_SERIES = {
    "DXY": "DX-Y.NYB",
    "SPX": "^GSPC",
    "NDX": "^IXIC",
    "BTC_USD": "BTC-USD",
    "IBIT": "IBIT",
}

BLOCKCHAIN_SERIES = {
    "hashrate": "hash-rate",
    "n_tx": "n-transactions",
    "n_unique_addr": "n-unique-addresses",
    "tx_vol_usd": "estimated-transaction-volume-usd",
    "mempool": "mempool-size",
}

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def default_transport(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Collector:
    def __init__(self, transport=None):
        self.transport = transport or default_transport

    def fetch_yahoo(self, name: str, days: int) -> list[dict]:
        url = YAHOO.format(YAHOO_SERIES[name], days)
        raw = self.transport(url)
        data = json.loads(raw.decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        close = res["indicators"]["quote"][0]["close"]
        rows = []
        for t, c in zip(ts, close):
            if c is None:
                continue
            rows.append({"ts": int(t), "date": time.strftime("%Y-%m-%d",
                        time.gmtime(t)), "value": float(c)})
        return rows

    def fetch_blockchain(self, name: str, days: int) -> list[dict]:
        url = BLOCKCHAIN.format(BLOCKCHAIN_SERIES[name], days)
        raw = self.transport(url)
        data = json.loads(raw.decode())
        rows = []
        for pt in data.get("values", []):
            rows.append({"ts": int(pt["x"]), "date": time.strftime("%Y-%m-%d",
                         time.gmtime(pt["x"])), "value": float(pt["y"])})
        return rows

    def collect_all(self, days: int) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for name in YAHOO_SERIES:
            try:
                out[name] = self.fetch_yahoo(name, days)
                print(f"{name}: {len(out[name])} точек", flush=True)
            except Exception as e:
                print(f"{name}: FAIL {e}", flush=True)
            time.sleep(0.4)
        for name in BLOCKCHAIN_SERIES:
            try:
                out[name] = self.fetch_blockchain(name, days)
                print(f"{name}: {len(out[name])} точек", flush=True)
            except Exception as e:
                print(f"{name}: FAIL {e}", flush=True)
            time.sleep(0.4)
        return out


def fetch_yahoo_hourly(transport, days: int) -> list[dict]:
    """BTC-USD hourly closes (for derivatives alignment)."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range={}d&interval=1h".format(days)
    raw = transport(url)
    data = json.loads(raw.decode())
    res = data["chart"]["result"][0]
    ts = res["timestamp"]
    close = res["indicators"]["quote"][0]["close"]
    rows = []
    for t, c in zip(ts, close):
        if c is None:
            continue
        rows.append({"ts": int(t), "date": time.strftime("%Y-%m-%d %H:%M",
                     time.gmtime(t)), "value": float(c)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=Path("data/market_data"))
    ap.add_argument("--days", type=int, default=400)
    ap.add_argument("--hourly", action="store_true", help="also fetch BTC-USD 1h")
    args = ap.parse_args()

    c = Collector()
    data = c.collect_all(args.days)
    if args.hourly:
        try:
            data["BTC_USD_1h"] = fetch_yahoo_hourly(c.transport, 60)
            print(f"BTC_USD_1h: {len(data['BTC_USD_1h'])} часов", flush=True)
        except Exception as e:
            print(f"BTC_USD_1h: FAIL {e}", flush=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in data.items():
        with open(args.out_dir / f"{name}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    print(f"сохранено {len(data)} серий в {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
