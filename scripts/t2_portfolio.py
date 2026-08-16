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
    names = [("BTC", "t2_paper_state.json"), ("ETH", "t2_paper_state_ethusd.json"),
             ("SOL", "t2_paper_state_solusd.json"), ("BNB", "t2_paper_state_bnbusd.json"),
             ("NEAR", "t2_paper_state_nearusd.json")]
    eqs, bhs = {}, {}
    for tag, fname in names:
        st = load_state(fname)
        eqs[tag] = float(st.get("equity", 10000.0))
        bhs[tag] = float(st.get("cash_equiv", 10000.0))
    port = sum(eqs.values()) / len(names)
    port_bh = sum(bhs.values()) / len(names)
    date = time.strftime("%Y-%m-%d")
    entry = {"date": date, "portfolio": round(port, 2), "bh": round(port_bh, 2),
             **{tag.lower(): round(v, 2) for tag, v in eqs.items()}}
    with open(OUT, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
