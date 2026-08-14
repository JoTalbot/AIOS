#!/usr/bin/env python3
"""Final verification of MA_LS_50_200 on the fixed engine: halves + per symbol."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from quant_earn_research import (  # noqa: E402
    FUNDING_BASE, FUNDING_STRESS, load_symbols, resample, run_with_funding, sig_ma,
)


def main() -> int:
    symbols = load_symbols()
    lens = sorted(len(df) for df in symbols.values())
    med_len = lens[len(lens) // 2]
    ts_50 = 0.0
    for df in symbols.values():
        if len(df) == med_len:
            ts_50 = float(df["timestamp_ms"].iloc[int(med_len * 0.50)])
            break
    last_ts = max(int(df["timestamp_ms"].iloc[-1]) for df in symbols.values())
    mid = (ts_50 + last_ts) / 2.0
    print(f"OOS50: {int(ts_50)} .. {last_ts}, mid {int(mid)}")

    # per-symbol on full OOS50
    per = {}
    for symbol, df in symbols.items():
        g = resample(df, 24)
        pos = sig_ma(g, 50, 200)
        rb = run_with_funding(g, pos, ts_50, FUNDING_BASE)
        if rb is None:
            continue
        per[symbol] = rb

    rows = sorted(per.items(), key=lambda x: -x[1]["net_pct"])
    pos_count = sum(1 for _, r in rows if r["net_pct"] > 0)
    avg = sum(r["net_pct"] for _, r in rows) / len(rows)
    print(f"MA_LS_50_200 OOS50: {pos_count}/{len(rows)} положительных, равновесный net {avg:+.2f}%")
    for s, r in rows:
        print(f"  {s:<7} gross {r['gross_pct']:>+8.2f}% fund {r['funding_pct']:>+6.2f}% "
              f"net {r['net_pct']:>+8.2f}% trades {r['trades']} shortD {r['short_days']:.0f}")

    # halves stability (net base) with proper upper bound
    def half_net(lo_ts, hi_ts):
        nets = []
        for symbol, df in symbols.items():
            g = resample(df, 24)
            pos = sig_ma(g, 50, 200)
            r = run_with_funding(g, pos, lo_ts, FUNDING_BASE, test_end=hi_ts)
            if r is not None:
                nets.append(r["net_pct"])
        return sum(nets) / len(nets) if nets else 0.0

    h1 = half_net(ts_50, mid)
    h2 = half_net(mid, last_ts)
    print(f"Половины (net base): half1 {h1:+.2f}% | half2 {h2:+.2f}%")

    report = {
        "per_symbol": {s: r for s, r in rows},
        "positive_symbols": pos_count,
        "total_symbols": len(rows),
        "avg_net_pct": round(avg, 2),
        "half1_net_pct": round(h1, 2),
        "half2_net_pct": round(h2, 2),
    }
    out = REPO_ROOT / "data" / "reports" / "earn_ma_ls_detail.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("report ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
