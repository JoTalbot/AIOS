#!/usr/bin/env python3
"""T2 portfolio 50/50 (BTC+ETH): daily mark-to-market of the two paper loops.

Reads the per-symbol state files and produces a combined equity view:
  portfolio_equity = 0.5 * equity_btc + 0.5 * equity_eth (on $10k each).
Appends to data/t2_portfolio_equity.jsonl for charting in the weekly digest.

Usage:
    python t2_portfolio.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path("/root/AIOS")
OUT = ROOT / "data" / "t2_portfolio_equity.jsonl"

def load_state(name: str) -> dict:
    p = ROOT / "data" / name
    return json.loads(p.read_text()) if p.exists() else {}

def main() -> int:
    import time
    btc = load_state("t2_paper_state.json")
    eth = load_state("t2_paper_state_ethusd.json")
    btc_eq = float(btc.get("equity", 10000.0))
    eth_eq = float(eth.get("equity", 10000.0))
    btc_bh = float(btc.get("cash_equiv", 10000.0))
    eth_bh = float(eth.get("cash_equiv", 10000.0))
    port = 0.5 * btc_eq + 0.5 * eth_eq
    port_bh = 0.5 * btc_bh + 0.5 * eth_bh
    date = time.strftime("%Y-%m-%d")
    entry = {"date": date, "portfolio": round(port, 2), "bh": round(port_bh, 2),
             "btc": round(btc_eq, 2), "eth": round(eth_eq, 2)}
    with open(OUT, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
