#!/usr/bin/env python3
"""Read-only analysis of collected orderbook snapshots.

Aggregates per-exchange spread/depth stats and cross-exchange mid disparities
(candidate HFT arbitrage windows). No trading, no mutation of data.

Usage:
    python scripts/analyze_orderbook_data.py [--db data/quant/orderbooks.sqlite]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np


def analyze(db_path: Path) -> dict:
    db = sqlite3.connect(db_path)
    rows = db.execute(
        "SELECT ts, exchange, symbol, bid, ask, mid, spread_bps, "
        "bid_depth_usd, ask_depth_usd FROM snapshots ORDER BY ts"
    ).fetchall()
    db.close()

    per_pair: dict[tuple, list] = defaultdict(list)
    for ts, ex, sym, bid, ask, mid, spread, bd, ad in rows:
        per_pair[(ex, sym)].append((ts, bid, ask, mid, spread, bd, ad))

    # 1) Per-exchange/symbol spread & depth stats
    pairs = []
    for (ex, sym), items in sorted(per_pair.items()):
        spreads = [x[4] for x in items]
        depths = [(x[5] + x[6]) / 2 for x in items]
        pairs.append(
            {
                "exchange": ex,
                "symbol": sym,
                "snapshots": len(items),
                "spread_bps_median": round(statistics.median(spreads), 3),
                "spread_bps_p95": round(np.percentile(spreads, 95), 3),
                "depth_usd_median": round(statistics.median(depths), 2),
                "ts_span_hours": round((items[-1][0] - items[0][0]) / 3600, 2),
            }
        )

    # 2) Cross-exchange mid disparity per symbol within a short time window.
    #    Group rows per symbol into 60s buckets; within a bucket compute the
    #    max|min mid gap in bps and count gaps >= 2 bps (arb candidate).
    disparity = []
    for sym in sorted({s for _, s, *_ in [(r[1], r[2]) for r in rows]}):
        bucket: dict[float, dict[str, float]] = defaultdict(dict)
        for ts, ex, s, bid, ask, mid, spread, bd, ad in rows:
            if s != sym:
                continue
            bucket[int(ts // 60)][ex] = mid
        gaps = []
        gap_ge_2bps = 0
        for bts, mids in bucket.items():
            if len(mids) < 2:
                continue
            vals = list(mids.values())
            hi, lo = max(vals), min(vals)
            gap_bps = (hi - lo) / lo * 10000 if lo > 0 else 0.0
            gaps.append(gap_bps)
            if gap_bps >= 2.0:
                gap_ge_2bps += 1
        disparity.append(
            {
                "symbol": sym,
                "buckets_with_data": len(bucket),
                "mid_gap_bps_median": round(statistics.median(gaps), 3) if gaps else 0.0,
                "mid_gap_bps_p95": round(np.percentile(gaps, 95), 3) if gaps else 0.0,
                "buckets_gap_ge_2bps": gap_ge_2bps,
            }
        )

    return {
        "total_snapshots": len(rows),
        "pairs": pairs,
        "cross_exchange_disparity": disparity,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=Path("data/quant/orderbooks.sqlite"))
    p.add_argument("--output", type=Path, default=Path("data/reports/orderbook_analysis.json"))
    args = p.parse_args()
    report = analyze(args.db)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "pairs"}, ensure_ascii=False))
    for pr in report["pairs"]:
        print(
            f"  {pr['exchange']:9s} {pr['symbol']:4s} n={pr['snapshots']:5d} "
            f"spread_med={pr['spread_bps_median']:7.3f}bps p95={pr['spread_bps_p95']:7.3f} "
            f"depth={pr['depth_usd_median']:12,.0f}$"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
