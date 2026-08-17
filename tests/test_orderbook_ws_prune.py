"""Tests for the orderbook ws retention pruner."""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prune_orderbook_ws import prune  # noqa: E402

NOW = 1_800_000_000.0


def _mk_db(path: Path, ts: float) -> None:
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS snapshots_ws (
        ts REAL NOT NULL, source TEXT NOT NULL, symbol TEXT NOT NULL,
        bid REAL NOT NULL, ask REAL NOT NULL, mid REAL NOT NULL, spread_bps REAL NOT NULL,
        bid_depth_usd REAL NOT NULL, ask_depth_usd REAL NOT NULL,
        bids_json TEXT NOT NULL, asks_json TEXT NOT NULL, latency_ms REAL NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS trades_ws (
        ts REAL NOT NULL, source TEXT NOT NULL, symbol TEXT NOT NULL,
        buy_vol REAL NOT NULL, sell_vol REAL NOT NULL, total_vol REAL NOT NULL,
        buy_frac REAL NOT NULL, n_trades INTEGER NOT NULL)""")
    con.commit()
    con.close()


def _insert(con: sqlite3.Connection, symbol: str, ts: float, n: int = 1, step: float = 1.0) -> None:
    for i in range(n):
        t = ts + i * step
        con.execute(
            "INSERT INTO snapshots_ws VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (t, "ws", symbol, 100.0, 100.1, 100.05, 10.0, 1000.0, 1000.0, "[]", "[]", 5.0),
        )
    con.commit()


def test_prune_keeps_raw_window_and_downsamples_middle(tmp_path, monkeypatch):
    db = tmp_path / "ob.sqlite"
    _mk_db(db, NOW)
    con = sqlite3.connect(db, timeout=30)
    _insert(con, "BTC", NOW - 60, n=4)          # raw window (kept)
    _insert(con, "ETH", NOW - 60, n=4)          # raw window (kept)
    _insert(con, "BTC", NOW - 8 * 86400, n=2)   # middle window, 1 minute bucket -> keep 1
    _insert(con, "ETH", NOW - 8 * 86400, n=2)   # middle window -> keep 1
    _insert(con, "BTC", NOW - 90 * 86400, n=3)  # tail -> deleted
    con.execute("INSERT INTO trades_ws VALUES (?,?,?,?,?,?,?,?)", (NOW - 90 * 86400, "ws", "BTC", 1, 1, 2, 0.5, 2))
    con.commit()
    con.close()

    monkeypatch.setattr("scripts.prune_orderbook_ws.time.time", lambda: NOW)
    stats = prune(db, raw_days=7, keep_days=60)

    con = sqlite3.connect(db)
    rows = con.execute("SELECT symbol, ts FROM snapshots_ws ORDER BY symbol, ts").fetchall()
    btc = [r for r in rows if r[0] == "BTC"]
    eth = [r for r in rows if r[0] == "ETH"]
    assert len(btc) == 4 + 1, btc        # 4 raw + 1 downsampled
    assert len(eth) == 4 + 1, eth        # 4 raw + 1 downsampled
    assert all(t >= NOW - 60 * 86400 for _, t in rows)
    assert con.execute("SELECT COUNT(*) FROM trades_ws").fetchone()[0] == 0
    assert stats["snapshots_ws_downsampled"] == 2
    assert stats["snapshots_ws_deleted_tail"] == 3
    con.close()


def test_prune_dry_run_changes_nothing(tmp_path, monkeypatch):
    db = tmp_path / "ob.sqlite"
    _mk_db(db, NOW)
    con = sqlite3.connect(db, timeout=30)
    _insert(con, "BTC", NOW - 90 * 86400, n=5)
    con.commit()
    con.close()

    monkeypatch.setattr("scripts.prune_orderbook_ws.time.time", lambda: NOW)
    prune(db, raw_days=7, keep_days=60, dry_run=True)

    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM snapshots_ws").fetchone()[0] == 5
    con.close()


def test_prune_rejects_invalid_window(tmp_path):
    db = tmp_path / "ob.sqlite"
    _mk_db(db, NOW)
    try:
        prune(db, raw_days=60, keep_days=7)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit for invalid window")
