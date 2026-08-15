#!/usr/bin/env python3
"""Inventory-aware market-making backtest prototype on collected orderbook snapshots.

Reads data/quant/orderbooks.sqlite (snapshots with full level-2 bids/asks JSON),
replays them and simulates a passive maker:
  - quotes bid/ask at mid +/- half_spread_bps, size = min(level depth, max_size);
  - fills only against incoming market orders approximated by price movement:
    a market buy executes our ask if next mid >= our ask; market sell if next mid <= bid;
  - inventory management: skew quotes by inventory (aversion), max position cap,
    quote refresh when mid moves beyond threshold;
  - PnL = collected spread - inventory risk (mark-to-market at end) - fees.

This is a RESEARCH prototype for feasibility estimation, not live trading.

Usage:
    python scripts/mm_proto_backtest.py --symbol BTC --exchange binance \
        [--half-spread-bps 2] [--max-size-usd 5000] [--inv-cap-usd 20000]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")


@dataclass
class MMState:
    inventory: float = 0.0          # base asset units (positive = long)
    cash: float = 0.0               # quote asset
    quote_side: str | None = None   # side of the standing quote
    quote_px: float = 0.0
    quote_size: float = 0.0
    fills: list = field(default_factory=list)
    n_quote: int = 0
    n_refresh: int = 0
    gross_pnl: float = 0.0
    fees: float = 0.0
    buy_cost_basis: list = field(default_factory=list)  # FIFO lots: (qty, px)


def load_snapshots(symbol: str, exchange: str) -> list[dict]:
    con = sqlite3.connect(DB)
    cur = con.execute(
        "SELECT ts, bid, ask, mid, spread_bps, bid_depth_usd, ask_depth_usd, "
        "bids_json, asks_json FROM snapshots WHERE symbol=? AND exchange=? "
        "ORDER BY ts", (symbol, exchange))
    rows = cur.fetchall()
    con.close()
    out = []
    for r in rows:
        out.append({
            "ts": r[0], "bid": r[1], "ask": r[2], "mid": r[3], "spread_bps": r[4],
            "bid_depth_usd": r[5], "ask_depth_usd": r[6],
            "bids": json.loads(r[7]) if r[7] else [],
            "asks": json.loads(r[8]) if r[8] else [],
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--exchange", default="binance")
    ap.add_argument("--half-spread-bps", type=float, default=2.0)
    ap.add_argument("--max-size-usd", type=float, default=5000.0)
    ap.add_argument("--inv-cap-usd", type=float, default=20000.0)
    ap.add_argument("--refresh-thresh-bps", type=float, default=5.0)
    ap.add_argument("--max-inv-usd", type=float, default=10000.0)
    args = ap.parse_args()

    snaps = load_snapshots(args.symbol, args.exchange)
    print(f"snapshots: {len(snaps)} ({args.symbol}@{args.exchange})", flush=True)
    if len(snaps) < 100:
        print("not enough data"); return 1

    half = args.half_spread_bps / 1e4
    thresh = args.refresh_thresh_bps / 1e4
    fee = 0.0005  # maker fee 0.05% (binance spot maker rebate is 0; use 0.02% for some pairs)
    st = MMState()
    st.cash = args.inv_cap_usd

    prev_mid = None
    for i, s in enumerate(snaps):
        mid = s["mid"]
        if prev_mid is None:
            prev_mid = mid
            continue
        # inventory mark
        inv_usd = st.inventory * mid
        # 1) fill check on the PREVIOUS quote
        if st.quote_side == "ask" and mid >= st.quote_px:
            # we sold at ask: realize spread vs FIFO buy lots
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
            if remaining > 1e-12:
                # short sale (no cost basis): mark at quote price
                st.gross_pnl += 0.0
            st.fills.append({"t": s["ts"], "side": "sell", "px": st.quote_px,
                             "qty": st.quote_size})
            st.quote_side = None
        elif st.quote_side == "bid" and mid <= st.quote_px:
            cost = st.quote_size * st.quote_px
            st.cash -= cost * (1 + fee)
            st.inventory += st.quote_size
            st.fees += cost * fee
            st.buy_cost_basis.append((st.quote_size, st.quote_px))
            st.fills.append({"t": s["ts"], "side": "buy", "px": st.quote_px,
                             "qty": st.quote_size})
            st.quote_side = None

        # 2) refresh or place quote: dual-sided, inventory-skewed sizes
        refresh = st.quote_side is None or abs(mid - prev_mid) / prev_mid > thresh
        if refresh:
            st.n_refresh += 1
            inv_pct = st.inventory * mid / args.inv_cap_usd  # -1..1, capped
            inv_pct = max(-1.0, min(1.0, inv_pct))
            # inventory skew: reduce size on the side that increases exposure
            base_size = args.max_size_usd / mid
            bid_size = base_size * max(0.2, 1.0 - inv_pct)      # if long, smaller bid
            ask_size = base_size * max(0.2, 1.0 + inv_pct)      # if long, bigger ask
            bid_px = mid * (1 - half)
            ask_px = mid * (1 + half)
            # if inventory extreme -> widen the reducing side
            if inv_pct > 0.5:
                bid_px = mid * (1 - half * 1.5)
            elif inv_pct < -0.5:
                ask_px = mid * (1 + half * 1.5)
            # place the side that reduces inventory first (as single quote for simplicity)
            if st.inventory > 0:
                st.quote_side = "ask"
                st.quote_px = ask_px
                st.quote_size = ask_size
            else:
                st.quote_side = "bid"
                st.quote_px = bid_px
                st.quote_size = bid_size
            st.n_quote += 1
        prev_mid = mid

    # mark-to-market
    final_mid = snaps[-1]["mid"]
    inv_val = st.inventory * final_mid
    total_pnl = st.gross_pnl + (st.cash - args.inv_cap_usd) + inv_val
    # round-trip: gross from spread, inventory PnL
    print("=" * 60)
    print(f"symbol={args.symbol} exchange={args.exchange} half_spread={args.half_spread_bps}bps")
    print(f"quotes placed: {st.n_quote}  refreshes: {st.n_refresh}  fills: {len(st.fills)}")
    print(f"final inventory: {st.inventory:.6f} ({inv_val:,.0f}$)  cash: {st.cash:,.0f}$")
    print(f"gross spread PnL: {st.gross_pnl:,.2f}$  fees: {st.fees:,.2f}$")
    print(f"NET PnL (incl inventory mtm): {total_pnl:,.2f}$  over {len(snaps)/7000:.1f}h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
