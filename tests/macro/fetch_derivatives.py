#!/usr/bin/env python3
"""Derivatives data collector (Binance Futures) + feature builders.

Collects (per symbol):
  - 1h klines with taker buy volume -> taker_buy_ratio (aggressor imbalance)
  - globalLongShortAccountRatio (account-position skew)
  - topLongShortAccountRatio (top-trader skew)
  - openInterestHist (OI change / OI delta)
  - premiumIndex (futures basis vs index)

NOTE: Binance is geo-blocked from some networks (HTTP 451). The collector takes
an injectable transport: tests use fixtures; production runs on a server where
the API is reachable. Historical depth: klines ~1500 bars/request (paginated),
ratios/OI ~30 days (API cap).

Usage:
    python fetch_derivatives.py --symbol BTC [--hours 720] [--out data/derivatives]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

FAPI = "https://fapi.binance.com"
UA = {"User-Agent": "Mozilla/5.0"}


def default_transport(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_klines(raw: bytes) -> list[dict]:
    """Binance kline -> rows with taker-buy ratio."""
    rows = []
    for k in json.loads(raw.decode()):
        vol = float(k[5])
        taker = float(k[9])
        rows.append({
            "open_ts": int(k[0]),
            "close": float(k[4]),
            "volume": vol,
            "taker_buy": taker,
            "taker_buy_ratio": (taker / vol) if vol > 0 else 0.5,
        })
    return rows


def parse_lsr(raw: bytes) -> list[dict]:
    rows = []
    for r in json.loads(raw.decode()):
        rows.append({
            "ts": int(r["timestamp"]),
            "lsr": float(r["longShortRatio"]),
            "long_share": float(r["longAccount"]),
        })
    return rows


def parse_oi(raw: bytes) -> list[dict]:
    rows = []
    for r in json.loads(raw.decode()):
        rows.append({"ts": int(r["timestamp"]), "oi": float(r["sumOpenInterest"])})
    return rows


class DerivCollector:
    def __init__(self, transport=None):
        self.transport = transport or default_transport

    def klines(self, sym: str, hours: int) -> list[dict]:
        """Paginated 1h klines (max 1500/request)."""
        out = []
        start = int(time.time() * 1000) - hours * 3600 * 1000
        while True:
            url = (f"{FAPI}/fapi/v1/klines?symbol={sym}USDT&interval=1h"
                   f"&startTime={start}&limit=1500")
            rows = parse_klines(self.transport(url))
            if not rows:
                break
            out.extend(rows)
            if len(rows) < 1500:
                break
            start = rows[-1]["open_ts"] + 3600 * 1000
            time.sleep(0.2)
        return out

    def global_lsr(self, sym: str, period: str = "1h") -> list[dict]:
        url = (f"{FAPI}/futures/data/globalLongShortAccountRatio?symbol={sym}USDT"
               f"&period={period}&limit=500")
        return parse_lsr(self.transport(url))

    def top_lsr(self, sym: str, period: str = "1h") -> list[dict]:
        url = (f"{FAPI}/futures/data/topLongShortAccountRatio?symbol={sym}USDT"
               f"&period={period}&limit=500")
        return parse_lsr(self.transport(url))

    def oi_hist(self, sym: str, period: str = "1h") -> list[dict]:
        url = (f"{FAPI}/futures/data/openInterestHist?symbol={sym}USDT"
               f"&period={period}&limit=500")
        return parse_oi(self.transport(url))

    def premium(self, sym: str) -> dict:
        url = f"{FAPI}/fapi/v1/premiumIndex?symbol={sym}USDT"
        raw = json.loads(self.transport(url).decode())
        return {"ts": int(raw["time"]), "mark": float(raw["markPrice"]),
                "index": float(raw["indexPrice"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--hours", type=int, default=720)
    ap.add_argument("--out", type=Path, default=Path("data/derivatives"))
    args = ap.parse_args()

    c = DerivCollector()
    args.out.mkdir(parents=True, exist_ok=True)
    data = {
        "klines": c.klines(args.symbol, args.hours),
        "global_lsr": c.global_lsr(args.symbol),
        "top_lsr": c.top_lsr(args.symbol),
        "oi": c.oi_hist(args.symbol),
        "premium": c.premium(args.symbol),
    }
    for name, rows in data.items():
        with open(args.out / f"{args.symbol}_{name}.json", "w") as f:
            json.dump(rows, f)
        n = len(rows) if isinstance(rows, list) else 1
        print(f"{name}: {n} записей", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
