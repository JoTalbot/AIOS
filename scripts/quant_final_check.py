#!/usr/bin/env python3
"""Final robustness check of the best candidates with a 50/50 split and
half-window stability. Read-only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from quant_strategy_research import load_symbols, resample  # noqa: E402
from quant_strategy_robust import add_rsi, run_on_df, sig_rsi2, sig_ma  # noqa: E402

COST_SIDE = 0.0015 + 0.0005 + 0.0005


def run_all(symbols, signal_fn, hours, test_start, test_end=None, with_rsi=False):
    total = 0.0
    n = 0
    for symbol, df in symbols.items():
        g = resample(df, hours)
        if with_rsi:
            g = add_rsi(g)
        r = run_on_df(g, signal_fn, test_start, test_end)
        total += r
        n += 1
    return round(total / n, 3) if n else 0.0


def main() -> int:
    symbols = load_symbols()
    lens = sorted(len(df) for df in symbols.values())
    med_len = lens[len(lens) // 2]
    first = 0.0
    for df in symbols.values():
        if len(df) == med_len:
            first = float(df["timestamp_ms"].iloc[int(med_len * 0.5)])
            break
    last_ts = max(int(df["timestamp_ms"].iloc[-1]) for df in symbols.values())
    mid = (first + last_ts) / 2.0
    print(f"50/50 split: {int(first)} .. {last_ts}, mid {int(mid)}")

    results = {}

    # MA daily LS with 50/50 split (out-of-sample = last 50%)
    for fast, slow, name in [(50, 200, "MA_LS_50_200"), (60, 240, "MA_LS_60_240")]:
        r = run_all(symbols, lambda d, f=fast, s=slow: sig_ma(d, f, s), 24, first)
        h1 = run_all(symbols, lambda d, f=fast, s=slow: sig_ma(d, f, s), 24, first, mid)
        h2 = run_all(symbols, lambda d, f=fast, s=slow: sig_ma(d, f, s), 24, mid, None)
        results[name] = {"oos50_pnl": r, "half1": h1, "half2": h2}
        print(f"{name}: OOS50 {r:+.2f}% | half1 {h1:+.2f}% | half2 {h2:+.2f}%")

    # RSI daily MR (30/70) with 50/50 split
    r = run_all(symbols, lambda d: sig_rsi2(d, 30, 70), 24, first, with_rsi=True)
    h1 = run_all(symbols, lambda d: sig_rsi2(d, 30, 70), 24, first, mid, with_rsi=True)
    h2 = run_all(symbols, lambda d: sig_rsi2(d, 30, 70), 24, mid, None, with_rsi=True)
    results["RSI_MR_30_70"] = {"oos50_pnl": r, "half1": h1, "half2": h2}
    print(f"RSI_MR_30_70: OOS50 {r:+.2f}% | half1 {h1:+.2f}% | half2 {h2:+.2f}%")

    # Portfolio version of MA_LS_50_200: 33 symbols, max 1 position, $1000,
    # synchronous (like production) — including SHORT side for reference.
    # Simpler: equal-weight already computed; add "best 5 by OOS50" subset.
    per_sym = {}
    for symbol, df in symbols.items():
        g = resample(df, 24)
        per_sym[symbol] = run_on_df(g, lambda d: sig_ma(d, 50, 200), first)
    best5 = sorted(per_sym.items(), key=lambda x: -x[1])[:5]
    worst5 = sorted(per_sym.items(), key=lambda x: x[1])[:5]
    print("best5:", [(s, f"{v:+.2f}") for s, v in best5])
    print("worst5:", [(s, f"{v:+.2f}") for s, v in worst5])

    out = REPO_ROOT / "data" / "reports" / "strategy_final_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "best5": dict(best5), "worst5": dict(worst5)},
                              indent=2, ensure_ascii=False))
    print("report ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
