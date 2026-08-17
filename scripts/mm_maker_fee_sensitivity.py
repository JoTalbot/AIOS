#!/usr/bin/env python3
"""Maker-fee sensitivity for MM candidates (BNB hypothesis from the queue model).

Replays naive/gated MM (scripts/mm_proto_backtest.run_mm) across a grid of
per-side fee rates from maker rebates (-0.05%) to taker-like fees (+0.10%),
finds the breakeven fee rate per mode, and compares against the venue fee
landscape (see docs/MM_BNB_MAKER_REBATE_2026-08-17_RU.md).

Read-only research; never trades.

Usage:
    python scripts/mm_maker_fee_sensitivity.py
        [--symbols BNB,BTC] [--out data/reports/mm_maker_fee_sensitivity.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.mm_proto_backtest import run_mm  # noqa: E402
from scripts.mm_ws_backtest import load_ws  # noqa: E402

# fee_rate grid (per side): maker rebate ... taker-like
FEE_GRID = [-0.0005, -0.0002, -0.0001, 0.0, 0.0001, 0.00025, 0.0005, 0.00075, 0.0010]


def breakeven_fee(points: list[tuple[float, float]]) -> float | None:
    """Interpolate the fee rate at which net_pnl crosses zero.

    points: [(fee_rate, net_pnl)] sorted by fee_rate ascending.
    Returns None when the curve never crosses zero.
    """

    pts = sorted(points)
    for (f0, p0), (f1, p1) in zip(pts, pts[1:]):
        if p0 is None or p1 is None:
            continue
        if p0 * p1 <= 0 and f1 != f0:
            t = p0 / (p0 - p1)
            return round(f0 + t * (f1 - f0), 6)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbols", default="BNB,BTC")
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "data" / "reports" / "mm_maker_fee_sensitivity.json")
    args = ap.parse_args()

    report: dict[str, dict] = {}
    for symbol in args.symbols.split(","):
        symbol = symbol.strip()
        snaps = load_ws(symbol)
        if len(snaps) < 1000:
            print(f"{symbol}: not enough data ({len(snaps)})", flush=True)
            continue
        row: dict[str, object] = {"snapshots": len(snaps)}
        for mode in ("naive", "gated"):
            pts: list[tuple[float, float]] = []
            detail: dict[str, dict] = {}
            for fee in FEE_GRID:
                res = run_mm(snaps, mode=mode, half_spread_bps=2.0,
                             max_size_usd=2000.0, inv_cap_usd=10000.0,
                             fee_rate=fee, hold_snaps=1, queue_model=True)
                net = float(res["net_pnl"])
                pts.append((fee, net))
                detail[str(fee)] = {"fills": res["fills"], "gross": res["gross_spread"],
                                    "fees": res["fees"], "net": net}
                print(f"{symbol} {mode} fee={fee:+.5f}: fills={res['fills']} "
                      f"gross={res['gross_spread']:.2f} fees={res['fees']:.2f} "
                      f"net={net:.2f}", flush=True)
            be = breakeven_fee(pts)
            print(f"{symbol} {mode} breakeven fee = {be}", flush=True)
            row[mode] = {"breakeven_fee": be, "curve": detail}
        report[symbol] = row

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"report -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
