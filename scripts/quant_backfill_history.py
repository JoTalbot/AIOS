#!/usr/bin/env python3
"""Backfill 1h history for short-history quant assets from Binance.

Extends each `data/quant/<SYM>/binance/<SYM>_1h.csv` backwards to ~5000 rows
(7 months) using paginated klines, preserving the existing tail (no overwrite
of fresh bars). Dead tickers MATIC/RNDR are skipped.

Usage:
    python scripts/quant_backfill_history.py [--target 5000] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUANT_DIR = REPO_ROOT / "data" / "quant"
SKIP = {"MATIC", "RNDR"}  # renamed to POL/RENDER

HOUR_MS = 3_600_000


def _fetch_klines(symbol: str, start_ms: int, limit: int = 1000) -> list[dict]:
    url = (
        "https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval=1h&startTime={int(start_ms)}&limit={limit}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AIOS-Quant-Backfill/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        rows = json.loads(resp.read().decode())
    return [
        {
            "timestamp_ms": int(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
        }
        for r in rows
    ]


def _read_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            try:
                rows.append(
                    {
                        "timestamp_ms": int(r["timestamp_ms"]),
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "volume": float(r["volume"]),
                    }
                )
            except (KeyError, ValueError):
                continue
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "open", "high", "low", "close", "volume", "collected_at"])
        for r in rows:
            writer.writerow(
                [r["timestamp_ms"], r["open"], r["high"], r["low"], r["close"], r["volume"], now]
            )


def _fetch_bybit(symbol: str, start_ms: int, limit: int = 1000) -> list[dict]:
    url = (
        "https://api.bybit.com/v5/market/kline"
        f"?category=spot&symbol={symbol}&interval=60&limit={limit}&start={int(start_ms)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AIOS-Quant-Backfill/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode())
    rows = data.get("result", {}).get("list", []) or []
    # Bybit returns newest-first; normalize to oldest-first
    out = []
    for r in rows:
        try:
            out.append(
                {
                    "timestamp_ms": int(r[0]),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": float(r[5]),
                }
            )
        except (IndexError, ValueError):
            continue
    return sorted(out, key=lambda x: x["timestamp_ms"])


def _fetch_any(symbol: str, start_ms: int) -> list[dict]:
    """Binance first, then Bybit fallback (e.g. KAS is not on Binance spot)."""
    try:
        return _fetch_klines(symbol, start_ms)
    except Exception:
        return _fetch_bybit(symbol, start_ms)


def backfill(symbol: str, target: int, dry_run: bool) -> dict:
    path = QUANT_DIR / symbol / "binance" / f"{symbol}_1h.csv"
    existing = _read_existing(path)
    by_ts = {r["timestamp_ms"]: r for r in existing}
    if len(by_ts) >= target:
        return {"symbol": symbol, "rows": len(by_ts), "added": 0, "status": "already_ok"}

    binance_symbol = f"{symbol}USDT"
    added = 0
    pages = 0
    # 1) Refresh the tail first: the existing series may have stopped being
    #    written (stale), so pull the most recent bars and merge them.
    try:
        fresh = _fetch_any(binance_symbol, int(time.time() * 1000) - 1000 * HOUR_MS)
    except Exception:
        fresh = []
    for r in fresh:
        by_ts.setdefault(r["timestamp_ms"], r)
    added += len(fresh)
    pages += 1
    # 2) Backfill the past until target length.
    while len(by_ts) < target and pages < 12:  # max 12k bars fetched
        min_ts = min(by_ts) if by_ts else int(time.time() * 1000)
        start_ms = min_ts - 1000 * HOUR_MS
        fetched = _fetch_any(binance_symbol, start_ms)
        if not fetched:
            break
        pages += 1
        n_before = len(by_ts)
        for r in fetched:
            by_ts.setdefault(r["timestamp_ms"], r)
        added += len(by_ts) - n_before
        if len(fetched) < 1000:  # reached the beginning of available history
            break
        time.sleep(0.25)

    rows = [by_ts[k] for k in sorted(by_ts)]
    if not dry_run and rows:
        _write_csv(path, rows)
    return {
        "symbol": symbol,
        "rows": len(rows),
        "added": added,
        "pages": pages,
        "status": "ok",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Only asset folders; skip service dirs and stray files.
    service_dirs = {"export", "models", "uniswap_v3", "clustering", "orders"}
    symbols = sorted(
        d.name for d in QUANT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
        and d.name not in SKIP and d.name not in service_dirs
    )
    report = []
    for symbol in symbols:
        try:
            res = backfill(symbol, args.target, args.dry_run)
            print(f"  {res['symbol']:6s} rows={res['rows']:5d} added={res['added']:4d} {res['status']}")
            report.append(res)
        except Exception as e:
            print(f"  {symbol:6s} ERROR: {str(e)[:100]}")
            report.append({"symbol": symbol, "status": "error", "error": str(e)[:100]})
        time.sleep(0.3)

    out = REPO_ROOT / "data" / "reports" / "quant_backfill_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("report ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
