#!/usr/bin/env python3
"""Score emitted MM signals against realized mid moves (accuracy tracking).

Reads data/reports/mm_signal_emitted.jsonl; for each emission finds the realized
mid at +60s/+180s from snapshots_ws; prints per-symbol accuracy.

Usage:
    python scripts/mm_signal_score.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")
LOG = Path("/root/AIOS/data/reports/mm_signal_emitted.jsonl")


def load_ws(symbol: str) -> tuple[np.ndarray, np.ndarray]:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT ts, mid FROM snapshots_ws WHERE symbol=? ORDER BY ts", (symbol,)).fetchall()
    con.close()
    return np.array([r[0] for r in rows]), np.array([r[1] for r in rows])


def main() -> int:
    if not LOG.exists():
        print("no emissions yet")
        return 0
    ems = [json.loads(l) for l in LOG.read_text().splitlines() if l]
    print(f"эмиссий: {len(ems)}", flush=True)
    cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    stats: dict[str, dict] = {}
    for e in ems:
        sym = e["symbol"]
        d = e["direction"]
        if d == "FLAT":
            continue
        if sym not in cache:
            cache[sym] = load_ws(sym)
        ts, mid = cache[sym]
        for H in (60, 180):
            j = int(np.searchsorted(ts, e["ts"] + H, side="left"))
            if j >= len(ts):
                continue
            realized = "UP" if mid[j] > e["mid"] else ("DOWN" if mid[j] < e["mid"] else "FLAT")
            st = stats.setdefault(sym, {"n": 0, "hits": 0, "flats": 0, "moves": 0})
            st["n"] += 1
            if realized == "FLAT":
                st["flats"] += 1
            else:
                st["moves"] += 1
                if realized == d:
                    st["hits"] += 1
    total_n = total_hits = total_moves = 0
    for sym, st in sorted(stats.items()):
        acc = st["hits"] / st["moves"] * 100 if st["moves"] else 0
        print(f"{sym}: сигналов={st['n']} движений={st['moves']} точных={st['hits']} "
              f"точность={acc:.0f}% flat={st['flats']}", flush=True)
        total_n += st["n"]
        total_hits += st["hits"]
        total_moves += st["moves"]
    if total_moves:
        print(f"ИТОГО: точность на движениях {total_hits/total_moves*100:.0f}% "
              f"({total_hits}/{total_moves}) из {total_n} сигналов", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
