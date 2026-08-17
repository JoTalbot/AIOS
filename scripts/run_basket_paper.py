#!/usr/bin/env python3
"""Top-10 basket paper benchmark (Edge Lab 2026-08-17).

The scoreboard winner (equal-weight top-10 majors basket) as a daily
mark-to-market paper tracker: monthly rebalance to equal weights, 0.1%
fee per rebalance leg, values appended to data/reports/basket_paper.jsonl.
Read-only; uses the same 1h data as the quant universe.

Usage:
    python scripts/run_basket_paper.py [--state data/reports/basket_paper_state.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
QUANT_DIR = REPO_ROOT / "data" / "quant"

TOP10 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "TRX", "TON", "ADA", "LINK"]
START_CAPITAL = 1000.0
FEE = 0.001
STATE_FILE = REPO_ROOT / "data" / "reports" / "basket_paper_state.json"
HISTORY_FILE = REPO_ROOT / "data" / "reports" / "basket_paper.jsonl"


def daily_close(symbol: str, day: str) -> float | None:
    """Last 1h close on or before `day` (YYYY-MM-DD)."""

    csv_paths = sorted(QUANT_DIR.glob(f"{symbol}/binance/{symbol}_1h.csv"))
    if not csv_paths:
        return None
    df = pd.read_csv(csv_paths[0])
    df["day"] = pd.to_datetime(df["timestamp_ms"], unit="ms").dt.strftime("%Y-%m-%d")
    sel = df[df["day"] <= day]
    if sel.empty:
        return None
    return float(sel.iloc[-1]["close"])


def mark(state: dict, day: str) -> dict | None:
    """Compute basket value at `day`; returns None when data incomplete."""

    prices = {}
    for sym in TOP10:
        px = daily_close(sym, day)
        if px is None:
            return None
        prices[sym] = px
    value = sum(state["holdings"].get(sym, 0.0) * px for sym, px in prices.items())
    return {"day": day, "value_usd": round(value, 2), "prices": prices}


def rebalance(state: dict, day: str, prices: dict[str, float]) -> dict:
    """Monthly rebalance to equal weights (fee per traded leg).

    On the very first rebalance the whole cash is invested equally.
    """

    value = sum(state["holdings"].get(sym, 0.0) * prices[sym] for sym in prices)
    if value <= 0 and state.get("cash_usd", 0.0) > 0:
        value = state["cash_usd"]
        state["cash_usd"] = 0.0
    target = value / len(prices)
    fees = 0.0
    holdings = {}
    for sym, px in prices.items():
        qty = state["holdings"].get(sym, 0.0)
        target_qty = target / px
        traded = abs(target_qty - qty) * px
        fees += traded * FEE
        holdings[sym] = target_qty
    state["holdings"] = holdings
    state["fees_paid_usd"] = state.get("fees_paid_usd", 0.0) + fees
    state["last_rebalance"] = day
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", type=Path, default=STATE_FILE)
    ap.add_argument("--history", type=Path, default=HISTORY_FILE)
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
    else:
        state = {
            "start_capital": START_CAPITAL,
            "cash_usd": START_CAPITAL,
            "holdings": {},
            "fees_paid_usd": 0.0,
            "last_rebalance": None,
            "started": today,
        }

    row = mark(state, today)
    if row is None:
        print("SKIP: неполные данные по корзине", flush=True)
        return 0

    # ежемесячный ребаланс: в первый прогон нового месяца (или самый первый)
    if state["last_rebalance"] is None or today[:7] != state["last_rebalance"][:7]:
        rebalance(state, today, row["prices"])
        row = mark(state, today)

    state["updated"] = today
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    entry = {
        "day": today,
        "value_usd": row["value_usd"],
        "fees_paid_usd": round(state.get("fees_paid_usd", 0.0), 4),
        "invested_usd": state["start_capital"],
        "pnl_pct": round((row["value_usd"] / state["start_capital"] - 1) * 100, 3),
    }
    with args.history.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
