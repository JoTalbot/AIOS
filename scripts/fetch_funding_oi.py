#!/usr/bin/env python3
"""Fetch funding rate + open interest history from Binance Futures (public, no key)."""
import json
import time
import urllib.request
from pathlib import Path

BASE = "https://fapi.binance.com"
OUT = Path("/root/AIOS/data/quant/funding_oi")
SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "LINK", "AVAX", "UNI",
           "NEAR", "LTC", "DOT", "SUI", "APT", "ARB", "OP", "INJ", "TIA", "SEI",
           "FET", "BONK", "PEPE", "SHIB", "TRX", "TON", "ETC", "FIL", "ATOM", "KAS",
           "WIF", "RENDER", "POL"]


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print("  retry", attempt, e)
            time.sleep(2 + attempt * 2)
    return None


def fetch_funding(sym):
    """All funding history via pagination (8h intervals)."""
    rows = []
    start = 0
    for page in range(60):
        url = (f"{BASE}/fapi/v1/fundingRate?symbol={sym}USDT"
               f"&startTime={start}&limit=1000")
        d = get(url)
        if not d:
            break
        rows.extend(d)
        if len(d) < 1000:
            break
        start = d[-1]["fundingTime"] + 1
        time.sleep(0.15)
    return rows


def fetch_oi(sym, period="1d"):
    """OI history (public data endpoint); depth depends on period."""
    rows = []
    end = int(time.time() * 1000)
    start = end - 400 * 24 * 3600 * 1000  # ~400 days back
    for page in range(10):
        url = (f"{BASE}/futures/data/openInterestHist?symbol={sym}USDT"
               f"&period={period}&startTime={start}&endTime={end}&limit=500")
        d = get(url)
        if not d:
            break
        rows.extend(d)
        if len(d) < 500:
            break
        start = d[-1]["timestamp"] + 1
        time.sleep(0.15)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, sym in enumerate(SYMBOLS):
        f = fetch_funding(sym)
        if f:
            with open(OUT / f"{sym}_funding.json", "w") as fh:
                json.dump(f, fh)
            t0 = f[0]["fundingTime"] / 86400000
            t1 = f[-1]["fundingTime"] / 86400000
            print(f"{sym}: funding n={len(f)} span {(t1-t0):.0f}d", flush=True)
            ok += 1
        oi = fetch_oi(sym, "1d")
        if oi:
            with open(OUT / f"{sym}_oi_1d.json", "w") as fh:
                json.dump(oi, fh)
            span = (oi[-1]["timestamp"] - oi[0]["timestamp"]) / 86400000
            print(f"        oi1d n={len(oi)} span {span:.0f}d", flush=True)
        time.sleep(0.2)
    print(f"done: {ok}/{len(SYMBOLS)} symbols")


if __name__ == "__main__":
    main()
