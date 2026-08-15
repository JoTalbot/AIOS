#!/usr/bin/env python3
"""Backfill per-exchange 1h history to N bars (~12 months) for the quant universe.

Extends `data/quant/<SYM>/<exchange>/<SYM>_1h.csv` backwards using the production
MarketDataCollector fetch/pair logic (ccxt, enableRateLimit=True), so pairing and
normalization match the live collector exactly. Existing rows are preserved via
timestamp-keyed merge (`MarketDataCollector._save_csv`). Binance is skipped by
default (all alive assets already have >= 10024 bars there).

Usage:
    python scripts/quant_backfill_exchanges.py [--target 8760] [--dry-run]
    python scripts/quant_backfill_exchanges.py --exchanges kucoin mexc --symbols BTC ETH
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from aios_core.quant.data_collector import MarketDataCollector, _utc_now

QUANT_DIR = REPO_ROOT / "data" / "quant"
HEADER = ["timestamp_ms", "open", "high", "low", "close", "volume", "collected_at"]
SKIP_SYMBOLS = {"MATIC", "RNDR"}  # delisted tickers, excluded from the quant universe
DEFAULT_EXCHANGES = ["kucoin", "mexc", "bybit", "kraken", "bitfinex", "bitstamp", "coinbase", "okx"]


HOUR_MS = 3_600_000


def _fetch_kraken(symbol: str, target: int, pause: float) -> list[list]:
    """Kraken OHLC: до 720 свечей от since; идём вперёд от (now - target часов).

    ccxt-петля обрывается рано (Kraken игнорирует forward-pagination), поэтому прямой REST.
    """
    pair_candidates = ["XBTUSD" if symbol == "BTC" else f"{symbol}USD", f"{symbol}USDT"]
    start_ms = int(time.time() * 1000) - target * HOUR_MS
    candles: dict[int, list] = {}
    for pair in pair_candidates:
        since_sec = start_ms // 1000
        candles.clear()
        try:
            for _ in range(1 + target // 700 + 1):
                resp = requests.get(
                    "https://api.kraken.com/0/public/OHLC",
                    params={"pair": pair, "interval": 60, "since": since_sec},
                    timeout=20,
                ).json()
                if resp.get("error"):
                    break
                result = resp.get("result") or {}
                rows = next((v for k, v in result.items() if k != "last"), [])
                if not rows:
                    break
                prev_since = since_sec
                for r in rows:
                    ts = int(r[0]) * 1000
                    candles[ts] = [ts, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[6])]
                since_sec = max(int(r[0]) for r in rows) + 60
                if since_sec <= prev_since or len(rows) < 2:
                    break
                time.sleep(1.2)
        except Exception as e:
            print(f"[kraken] {symbol}/{pair}: {type(e).__name__} {e}", flush=True)
        if candles:
            break
        time.sleep(pause)
    return [candles[k] for k in sorted(candles)][-target:]


def _fetch_bitfinex(symbol: str, target: int, pause: float) -> list[list]:
    """Bitfinex candles hist: до 10000 свечей за один запрос (sort=1), плюс медленный pacing."""
    start_ms = int(time.time() * 1000) - target * HOUR_MS
    end_ms = int(time.time() * 1000)
    for suffix in ("UST", "USD"):
        try:
            resp = requests.get(
                f"https://api-pub.bitfinex.com/v2/candles/trade:1h:t{symbol}{suffix}/hist",
                params={"start": start_ms, "end": end_ms, "limit": 10000, "sort": 1},
                timeout=30,
            ).json()
            if isinstance(resp, list) and resp and isinstance(resp[0], list):
                # Формат bitfinex: [mts, open, CLOSE, HIGH, LOW, volume]
                return [[int(r[0]), float(r[1]), float(r[3]), float(r[4]), float(r[2]), float(r[5])]
                        for r in resp][-target:]
        except Exception as e:
            print(f"[bitfinex] {symbol}{suffix}: {type(e).__name__} {e}", flush=True)
        time.sleep(pause)
    return []


def _symbols() -> list[str]:
    """Quant universe: dirs with a binance 1h series, minus dead tickers."""
    return sorted(
        p.name for p in QUANT_DIR.iterdir()
        if p.is_dir() and (p / "binance" / f"{p.name}_1h.csv").exists() and p.name not in SKIP_SYMBOLS
    )


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as stream:
        return max(0, sum(1 for _ in stream) - 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=8760, help="1h bars per series (8760 ~= 12 months)")
    parser.add_argument("--exchanges", nargs="*", default=DEFAULT_EXCHANGES)
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2, help="pause between symbols, seconds")
    parser.add_argument("--retries", type=int, default=1, help="fetch attempts per series with backoff")
    args = parser.parse_args()

    symbols = args.symbols or _symbols()
    collector = MarketDataCollector(symbols=symbols, exchanges=args.exchanges)
    print(f"symbols={len(symbols)} exchanges={args.exchanges} target={args.target}", flush=True)

    summary: dict[str, dict[str, int]] = {}
    for exchange in args.exchanges:
        stats = {"ok": 0, "no_pair": 0, "fetch_fail": 0, "already": 0}
        summary[exchange] = stats
        for symbol in symbols:
            path = QUANT_DIR / symbol / exchange / f"{symbol}_1h.csv"
            have = _count_rows(path)
            if have >= args.target:
                stats["already"] += 1
                continue
            pair = collector._pair_for(exchange, symbol)
            if not pair:
                stats["no_pair"] += 1
                print(f"[{exchange}] {symbol}: no pair -> skip", flush=True)
                continue
            if args.dry_run:
                print(f"[{exchange}] {symbol}: have={have}, would fetch {args.target} ({pair})", flush=True)
                continue
            rows: list[list] = []
            for attempt in range(max(1, args.retries)):
                if exchange == "kraken":
                    rows = _fetch_kraken(symbol, args.target, args.sleep)
                elif exchange == "bitfinex":
                    rows = _fetch_bitfinex(symbol, args.target, args.sleep)
                else:
                    rows = collector._fetch_ohlcv(exchange, pair, "1h", limit=args.target)
                if rows:
                    break
                backoff = args.sleep * (4 ** attempt) + 1.0
                print(f"[{exchange}] {symbol}: attempt {attempt + 1} failed, backoff {backoff:.0f}s", flush=True)
                time.sleep(backoff)
            if not rows:
                stats["fetch_fail"] += 1
                print(f"[{exchange}] {symbol}: FETCH FAIL, keep existing {have}", flush=True)
                continue
            out = [[int(r[0]), r[1], r[2], r[3], r[4], r[5], _utc_now()] for r in rows]
            collector._save_csv(path, out, HEADER)
            stats["ok"] += 1
            print(f"[{exchange}] {symbol}: {have} -> {_count_rows(path)} bars ({pair})", flush=True)
            time.sleep(args.sleep)

    print("=== SUMMARY ===", flush=True)
    for exchange, stats in summary.items():
        print(f"{exchange}: {stats}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
