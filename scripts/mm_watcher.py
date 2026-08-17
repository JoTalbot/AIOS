#!/usr/bin/env python3
"""Wait until any (exchange, symbol) pair reaches N orderbook snapshots,
then run the market-making simulator and persist the report. Read-only."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DB = Path("data/quant/orderbooks.sqlite")
MIN_SNAPSHOTS = int(sys.argv[1]) if len(sys.argv) > 1 else 1000


def max_per_pair() -> int:
    db = sqlite3.connect(DB)
    try:
        return db.execute(
            "SELECT MAX(cnt) FROM (SELECT COUNT(*) AS cnt FROM snapshots GROUP BY exchange, symbol)"
        ).fetchone()[0] or 0
    finally:
        db.close()


def main() -> int:
    print(f"watcher: waiting for >= {MIN_SNAPSHOTS} snapshots per pair", flush=True)
    while True:
        n = max_per_pair()
        print(f"watcher: max per pair = {n}", flush=True)
        if n >= MIN_SNAPSHOTS:
            break
        time.sleep(60)
    print("watcher: threshold reached, running market-making simulator", flush=True)
    cmd = [
        sys.executable,
        "scripts/run_market_making_simulator.py",
        "--min-snapshots", str(MIN_SNAPSHOTS),
    ]
    subprocess.run(cmd, check=False)
    print("watcher: done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
