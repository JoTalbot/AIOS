#!/usr/bin/env python3
"""P2: early sentiment-price link test (N2-lite).

For each news item in news_sentiment.jsonl: find BTC/ETH mid at news time and
at +30/+60 min (from snapshots_ws); compute correlation sentiment -> forward
return. Early indicator only (data so far is hours, not weeks).

Usage:
    python scripts/sentiment_price_test.py
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/root/AIOS")
DB = ROOT / "data" / "quant" / "orderbooks.sqlite"
NEWS = ROOT / "data" / "quant" / "news_sentiment.jsonl"


def load_mids(symbol: str) -> tuple[np.ndarray, np.ndarray]:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT ts, mid FROM snapshots_ws WHERE symbol=? ORDER BY ts", (symbol,)).fetchall()
    con.close()
    return np.array([r[0] for r in rows]), np.array([r[1] for r in rows])


def main() -> int:
    if not NEWS.exists():
        print("нет новостей")
        return 0
    rows = [json.loads(l) for l in NEWS.read_text().splitlines() if l]
    print(f"новостей: {len(rows)}", flush=True)
    if not rows:
        return 0

    cache = {}
    pairs: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        # время новости (ts в секундах)
        ts = float(r.get("ts", 0))
        if not ts:
            continue
        sent = float(r.get("sentiment", 0.0))
        coins = r.get("coins", []) or []
        syms = [c for c in ("BTC", "ETH") if c in str(coins) or not coins]
        if not syms:
            syms = ["BTC"]
        for sym in syms:
            if sym not in cache:
                cache[sym] = load_mids(sym)
            t, m = cache[sym]
            for H, tag in ((1800, "30m"), (3600, "1h")):
                j0 = int(np.searchsorted(t, ts, side="right")) - 1
                j1 = int(np.searchsorted(t, ts + H, side="left"))
                if j0 < 0 or j0 >= len(t) or j1 >= len(t) or m[j0] <= 0:
                    continue
                ret = (m[j1] / m[j0] - 1.0) * 100.0  # %
                pairs[f"{sym}@{tag}"].append((sent, ret))

    print(f"{'пара':<10} {'n':>4} {'corr':>7} {'avg_ret_pos':>11} {'avg_ret_neg':>11}", flush=True)
    for key in sorted(pairs):
        vals = pairs[key]
        sents = np.array([v[0] for v in vals])
        rets = np.array([v[1] for v in vals])
        corr = float(np.corrcoef(sents, rets)[0, 1]) if len(vals) > 2 else float("nan")
        pos = rets[sents > 0.2].mean() if (sents > 0.2).any() else float("nan")
        neg = rets[sents < -0.2].mean() if (sents < -0.2).any() else float("nan")
        print(f"{key:<10} {len(vals):>4} {corr:>+7.3f} {pos:>+10.3f}% {neg:>+10.3f}%", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
