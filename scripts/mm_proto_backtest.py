#!/usr/bin/env python3
"""Inventory-aware market-making backtest prototype on collected orderbook snapshots.

Reads data/quant/orderbooks.sqlite (snapshots with full level-2 bids/asks JSON),
replays them and simulates a passive maker with per-snapshot requoting:

  - naive mode: dual-sided quotes at mid +/- half_spread, inventory-skewed sizes;
  - gated mode: CatBoost direction model trained on the first 70% of the stream;
    quote bid when prob_up > thr (expect rise), ask when prob_up < thr (expect fall),
    no quote otherwise; inventory extremes force a reducing quote.

Fill model: a quote set at snapshot i-1 fills at i if mid crossed the quote price.
PnL = realized spread (FIFO) - fees + inventory mark-to-market.

This is a RESEARCH prototype, not live trading.

Usage:
    python scripts/mm_proto_backtest.py --symbol BTC --exchange binance \
        [--half-spread-bps 2] [--max-size-usd 5000] [--inv-cap-usd 20000] [--mode naive|gated]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")


@dataclass
class MMState:
    inventory: float = 0.0
    cash: float = 0.0
    quote_side: str | None = None
    quote_px: float = 0.0
    quote_size: float = 0.0
    fills: list = field(default_factory=list)
    n_refresh: int = 0
    gross_pnl: float = 0.0
    fees: float = 0.0
    buy_cost_basis: list = field(default_factory=list)


def load_snapshots(symbol: str, exchange: str) -> list[dict]:
    con = sqlite3.connect(DB)
    cur = con.execute(
        "SELECT ts, bid, ask, mid, spread_bps, bid_depth_usd, ask_depth_usd, "
        "bids_json, asks_json, latency_ms FROM snapshots WHERE symbol=? AND exchange=? "
        "ORDER BY ts", (symbol, exchange))
    rows = cur.fetchall()
    con.close()
    out = []
    for r in rows:
        out.append({"ts": r[0], "bid": r[1], "ask": r[2], "mid": r[3],
                    "spread_bps": r[4], "bid_depth_usd": r[5], "ask_depth_usd": r[6],
                    "bids": json.loads(r[7]) if r[7] else [],
                    "asks": json.loads(r[8]) if r[8] else [],
                    "latency_ms": r[9]})
    return out


def book_vol(levels, upto: int) -> float:
    return sum(q for _, q in levels[:upto])


def _fill_check(st: MMState, mid: float, fee: float):
    """Process fill of the standing quote if mid crossed it. Returns True if filled."""
    if st.quote_side == "ask" and mid >= st.quote_px:
        proceeds = st.quote_size * st.quote_px
        st.cash += proceeds * (1 - fee)
        st.inventory -= st.quote_size
        st.fees += proceeds * fee
        remaining = st.quote_size
        while remaining > 1e-12 and st.buy_cost_basis:
            lot_qty, lot_px = st.buy_cost_basis[0]
            used = min(remaining, lot_qty)
            st.gross_pnl += used * (st.quote_px - lot_px)
            remaining -= used
            if used >= lot_qty - 1e-12:
                st.buy_cost_basis.pop(0)
            else:
                st.buy_cost_basis[0] = (lot_qty - used, lot_px)
        st.fills.append({"side": "sell", "px": st.quote_px, "qty": st.quote_size})
        st.quote_side = None
        return True
    if st.quote_side == "bid" and mid <= st.quote_px:
        cost = st.quote_size * st.quote_px
        st.cash -= cost * (1 + fee)
        st.inventory += st.quote_size
        st.fees += cost * fee
        st.buy_cost_basis.append((st.quote_size, st.quote_px))
        st.fills.append({"side": "buy", "px": st.quote_px, "qty": st.quote_size})
        st.quote_side = None
        return True
    return False


def run_mm(snaps: list[dict], *, mode: str = "naive", half_spread_bps: float = 2.0,
           max_size_usd: float = 2000.0, inv_cap_usd: float = 10000.0,
           up_thr: float = 0.55, down_thr: float = 0.45, fee_rate: float = 0.0005,
           hold_snaps: int = 1) -> dict:
    """Replay snapshots as a passive maker; requote per snapshot but HOLD the quote
    for `hold_snaps` snapshots so mid has a chance to cross it (realistic for 1Hz
    streams; for ~9s REST streams a 1-snapshot hold means a 9s quote lifetime)."""
    half = half_spread_bps / 1e4
    fee = fee_rate
    st = MMState()
    st.cash = inv_cap_usd
    n_gated = 0
    n_quoted = 0
    inv_band = 0.05 * inv_cap_usd
    hold_left = 0

    prob = None
    if mode == "gated":
        from mm_microstructure_signal import features
        from catboost import CatBoostClassifier

        F, Y = features(snaps)
        feat_names = list(F[0].keys())
        X = np.array([[F[i][k] for k in feat_names] for i in range(len(F))])
        y = Y[:, 0]
        mask = y >= 0
        idxs = mask.nonzero()[0]
        n = int(len(idxs) * 0.70)
        cut = idxs[n]
        model = CatBoostClassifier(iterations=300, depth=4, learning_rate=0.05,
                                   loss_function="Logloss", eval_metric="AUC",
                                   random_seed=42, verbose=0)
        model.fit(X[idxs[:n]], y[idxs[:n]].astype(int))
        prob = model.predict_proba(X)[:, 1]
        start_i = max(1, cut)
    else:
        start_i = 1

    for i in range(start_i, len(snaps)):
        s = snaps[i]
        mid = s["mid"]
        _fill_check(st, mid, fee)
        if st.quote_side is not None:
            if hold_left > 0:
                hold_left -= 1
                continue  # keep the quote standing
            else:
                st.quote_side = None  # quote expired
        # requote
        st.n_refresh += 1
        base_size = max_size_usd / mid
        bid_px = mid * (1 - half)
        ask_px = mid * (1 + half)
        inv_usd = st.inventory * mid
        if mode == "naive":
            if st.inventory > 0:
                st.quote_side, st.quote_px, st.quote_size = "ask", ask_px, base_size
            else:
                st.quote_side, st.quote_px, st.quote_size = "bid", bid_px, base_size
            n_quoted += 1
            hold_left = hold_snaps
        else:  # gated
            p_up = float(prob[i])
            if inv_usd > inv_band:
                st.quote_side, st.quote_px, st.quote_size = "ask", ask_px, base_size
                n_quoted += 1
                hold_left = hold_snaps
            elif inv_usd < -inv_band:
                st.quote_side, st.quote_px, st.quote_size = "bid", bid_px, base_size
                n_quoted += 1
                hold_left = hold_snaps
            elif p_up > up_thr:
                st.quote_side, st.quote_px, st.quote_size = "bid", bid_px, base_size
                n_quoted += 1
                hold_left = hold_snaps
            elif p_up < down_thr:
                st.quote_side, st.quote_px, st.quote_size = "ask", ask_px, base_size
                n_quoted += 1
                hold_left = hold_snaps
            else:
                st.quote_side = None
                n_gated += 1

    final_mid = snaps[-1]["mid"]
    inv_val = st.inventory * final_mid
    total_pnl = st.gross_pnl + (st.cash - inv_cap_usd) + inv_val
    return {"quotes": n_quoted, "fills": len(st.fills), "gated": n_gated,
            "inventory": round(st.inventory, 6),
            "gross_spread": round(st.gross_pnl, 2), "fees": round(st.fees, 2),
            "net_pnl": round(total_pnl, 2), "hours": round(len(snaps) / 7000, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--exchange", default="binance")
    ap.add_argument("--half-spread-bps", type=float, default=2.0)
    ap.add_argument("--max-size-usd", type=float, default=2000.0)
    ap.add_argument("--inv-cap-usd", type=float, default=10000.0)
    ap.add_argument("--mode", default="naive", choices=["naive", "gated"])
    ap.add_argument("--hold-snaps", type=int, default=1)
    args = ap.parse_args()

    snaps = load_snapshots(args.symbol, args.exchange)
    print(f"snapshots: {len(snaps)} ({args.symbol}@{args.exchange}) mode={args.mode}", flush=True)
    if len(snaps) < 500:
        print("not enough data")
        return 1
    res = run_mm(snaps, mode=args.mode, half_spread_bps=args.half_spread_bps,
                 max_size_usd=args.max_size_usd, inv_cap_usd=args.inv_cap_usd,
                 hold_snaps=args.hold_snaps)
    print(json.dumps(res, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
