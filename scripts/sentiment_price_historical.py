#!/usr/bin/env python3
"""Historical sentiment-price link test.

For each historical news item (with sentiment): match the headline's publication
date to 1h OHLCV prices (binance) of the mentioned coins (or BTC if none), then
compute forward returns over +1h / +24h / +72h / +7d and correlation with
sentiment, plus event-study averages for positive vs negative news.

Usage:
    python scripts/sentiment_price_historical.py [--min-n 30]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/root/AIOS")
sys.path.insert(0, str(REPO / "scripts"))

import quant_monthly_backtest as qmb

NEWS = REPO / "data" / "quant" / "news_historical.jsonl"

COIN_ALIASES = {
    "BTC": ["bitcoin", "btc"], "ETH": ["ethereum", "eth", "ether"],
    "SOL": ["solana", "sol"], "XRP": ["xrp", "ripple"],
    "BNB": ["bnb", "binance coin", "binance"], "DOGE": ["dogecoin", "doge"],
    "ADA": ["cardano", "ada"], "TRX": ["tron", "trx"],
    "TON": ["toncoin", "ton"], "LINK": ["chainlink", "link"],
    "AVAX": ["avalanche", "avax"], "LTC": ["litecoin", "ltc"],
    "DOT": ["polkadot", "dot"], "UNI": ["uniswap", "uni"],
    "NEAR": ["near protocol", "near"], "SUI": ["sui"],
    "APT": ["aptos", "apt"], "ARB": ["arbitrum", "arb"],
    "OP": ["optimism"], "INJ": ["injective", "inj"],
}


def detect_coins(title: str) -> list[str]:
    t = title.lower()
    found = []
    for sym, aliases in COIN_ALIASES.items():
        for a in aliases:
            if re.search(rf"\b{a}\b", t):
                found.append(sym)
                break
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-n", type=int, default=30)
    args = ap.parse_args()

    if not NEWS.exists():
        print("нет исторических новостей")
        return 0
    rows = [json.loads(l) for l in NEWS.read_text().splitlines() if l]
    scored = [r for r in rows if "sentiment" in r]
    print(f"новостей: {len(rows)}, с сентиментом: {len(scored)}", flush=True)
    if len(scored) < args.min_n:
        print(f"мало для теста (нужно >= {args.min_n})")
        return 0

    # грузим цены (binance 1h)
    prices: dict[str, pd.DataFrame] = {}
    symbols, _ = qmb.load_symbols("binance")
    for sym, df in symbols.items():
        prices[sym] = df[["timestamp_ms", "close"]].copy()
        prices[sym]["dt"] = pd.to_datetime(prices[sym]["timestamp_ms"], unit="ms", utc=True)

    results: dict[str, list[tuple[float, float]]] = defaultdict(list)
    matched = 0
    for r in scored:
        # время: из pubDate (RSS) или snapshot date
        pub = r.get("pub", "")
        m = re.search(r"\d{1,2} \w+ \d{4} \d{2}:\d{2}", pub)
        if not m:
            continue
        try:
            t = pd.to_datetime(m.group(0), format="%d %b %Y %H:%M", utc=True)
        except Exception:
            continue
        coins = detect_coins(r["title"])
        if not coins:
            coins = ["BTC"]
        sent = float(r["sentiment"])
        for sym in coins:
            if sym not in prices:
                continue
            df = prices[sym]
            row = df[df["dt"] <= t]
            if row.empty:
                continue
            base = float(row["close"].iloc[-1])
            if base <= 0:
                continue
            for H, tag in ((3600, "1h"), (86400, "24h"), (259200, "3d"), (604800, "7d")):
                fut = df[(df["dt"] > t) & (df["dt"] <= t + pd.Timedelta(seconds=H))]
                if fut.empty:
                    continue
                ret = (float(fut["close"].iloc[-1]) / base - 1.0) * 100.0
                results[f"{sym}@{tag}"].append((sent, ret))
            matched += 1

    print(f"совпадений новость→цена: {matched}", flush=True)
    print(f"\n{'пара':<10} {'n':>5} {'corr':>8} {'pos_avg':>9} {'neg_avg':>9} {'diff':>9}", flush=True)
    total = 0
    for key in sorted(results):
        vals = results[key]
        sents = np.array([v[0] for v in vals])
        rets = np.array([v[1] for v in vals])
        if len(vals) < 10:
            continue
        corr = float(np.corrcoef(sents, rets)[0, 1])
        pos = rets[sents > 0.2].mean() if (sents > 0.2).any() else float("nan")
        neg = rets[sents < -0.2].mean() if (sents < -0.2).any() else float("nan")
        diff = pos - neg if not (np.isnan(pos) or np.isnan(neg)) else float("nan")
        print(f"{key:<10} {len(vals):>5} {corr:>+8.3f} {pos:>+8.3f}% {neg:>+8.3f}% {diff:>+8.3f}%", flush=True)
        total += len(vals)

    # агрегат по горизонту (все монеты)
    print("\nагрегат по горизонту (все монеты):", flush=True)
    for tag in ("1h", "24h", "3d", "7d"):
        vals = []
        for k, v in results.items():
            if k.endswith(f"@{tag}"):
                vals.extend(v)
        if len(vals) < 20:
            continue
        sents = np.array([v[0] for v in vals])
        rets = np.array([v[1] for v in vals])
        corr = float(np.corrcoef(sents, rets)[0, 1])
        pos = rets[sents > 0.2].mean() if (sents > 0.2).any() else float("nan")
        neg = rets[sents < -0.2].mean() if (sents < -0.2).any() else float("nan")
        print(f"  {tag}: n={len(vals)} corr={corr:+.3f} pos={pos:+.3f}% neg={neg:+.3f}% "
              f"diff={pos-neg:+.3f}%", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
