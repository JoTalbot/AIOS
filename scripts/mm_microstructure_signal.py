#!/usr/bin/env python3
"""MM stage 2: microstructure direction signal from orderbook snapshots.

Per (symbol, exchange) stream, computes features from the raw L2 book:
  - mid, microprice, spread_bps (from raw levels)
  - order book imbalance OBI_k at depth k (1, 5, 10): (bd-ask)/(bd+ask) by volume
  - depth-weighted mid (microprice) offset
  - mid return over last 1/3/5 snapshots, OBI change
  - top-of-book size ratio, depth asymmetry
Target: sign of mid move over next h snapshots (h=1,3,5).

Honest evaluation: per-stream time split 70/30 (no shuffling), CatBoost vs
persistence baseline; report AUC / hit@thr / coverage. Then integration mode:
--gate runs the MM prototype with signal-gated quoting and compares PnL.

Usage:
    python scripts/mm_microstructure_signal.py --symbol BTC --exchange binance [--gate]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

import numpy as np

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")


def load_snapshots(symbol: str, exchange: str = "binance", table: str = "snapshots") -> list[dict]:
    con = sqlite3.connect(DB)
    if table == "snapshots_ws":
        cur = con.execute(
            "SELECT ts, bid, ask, mid, spread_bps, bid_depth_usd, ask_depth_usd, "
            "bids_json, asks_json, latency_ms FROM snapshots_ws WHERE symbol=? "
            "ORDER BY ts", (symbol,))
    else:
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


def features(snaps: list[dict]) -> tuple[list[dict], np.ndarray]:
    """Vectorized-ish feature building over a stream."""
    n = len(snaps)
    mids = np.array([s["mid"] for s in snaps])
    F = []
    for i in range(n):
        s = snaps[i]
        bd1 = book_vol(s["bids"], 1)
        ad1 = book_vol(s["asks"], 1)
        bd5 = book_vol(s["bids"], 5)
        ad5 = book_vol(s["asks"], 5)
        bd10 = book_vol(s["bids"], 10)
        ad10 = book_vol(s["asks"], 10)
        obi1 = (bd1 - ad1) / (bd1 + ad1 + 1e-12)
        obi5 = (bd5 - ad5) / (bd5 + ad5 + 1e-12)
        obi10 = (bd10 - ad10) / (bd10 + ad10 + 1e-12)
        # microprice: volume-weighted mid
        micro = (s["ask"] * bd1 + s["bid"] * ad1) / (bd1 + ad1 + 1e-12)
        spread = (s["ask"] - s["bid"]) / mids[i] * 1e4 if mids[i] else 0.0
        top_ratio = bd1 / (ad1 + 1e-12)
        f = {
            "obi1": obi1, "obi5": obi5, "obi10": obi10,
            "micro_off": (micro - mids[i]) / mids[i] * 1e4 if mids[i] else 0.0,
            "spread_bps": spread,
            "top_ratio": top_ratio,
            "depth_asym": (bd10 - ad10) / (bd10 + ad10 + 1e-12),
            "latency": s.get("latency_ms") or 0.0,
        }
        F.append(f)
    # lagged mid returns (only past info)
    for k, name in ((1, "ret1"), (3, "ret3"), (5, "ret5")):
        r = np.zeros(n)
        for i in range(k, n):
            r[i] = (mids[i] / mids[i - k] - 1.0) * 1e4 if mids[i - k] else 0.0
        for i in range(n):
            F[i][name] = float(r[i])
    # obi changes (lagged)
    for k, name in ((1, "dobi1"), (3, "dobi5")):
        col = "obi1" if k == 1 else "obi5"
        for i in range(n):
            if i >= k:
                F[i][name] = F[i][col] - F[i - k][col]
            else:
                F[i][name] = 0.0
    # targets: mid move over next h snapshots (h=1,3,5)
    Y = np.zeros((n, 3))
    for h in (1, 3, 5):
        for i in range(n - h):
            Y[i, 0 if h == 1 else (1 if h == 3 else 2)] = 1.0 if mids[i + h] > mids[i] else 0.0
        # last h rows: no future -> mark -1 (excluded)
        for i in range(max(0, n - h), n):
            Y[i, 0 if h == 1 else (1 if h == 3 else 2)] = -1.0
    return F, Y


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--exchange", default="binance")
    ap.add_argument("--table", default="snapshots", choices=["snapshots", "snapshots_ws"])
    ap.add_argument("--min-snaps", type=int, default=500)
    ap.add_argument("--gate", action="store_true", help="run gated MM comparison")
    args = ap.parse_args()

    snaps = load_snapshots(args.symbol, args.exchange, args.table)
    print(f"snapshots: {len(snaps)} ({args.symbol}@{args.exchange} table={args.table})", flush=True)
    if len(snaps) < args.min_snaps:
        print("not enough data"); return 1

    F, Y = features(snaps)
    feat_names = list(F[0].keys())
    X = np.array([[F[i][k] for k in feat_names] for i in range(len(F))])

    from catboost import CatBoostClassifier

    print("features:", feat_names, flush=True)
    mids = np.array([s["mid"] for s in snaps])
    # HONEST target: only observations where the mid actually MOVES over the horizon.
    # Flat observations (mid unchanged) are excluded - predicting "no move" is trivial
    # and useless for direction signal.
    for hi, (h, name) in enumerate(((1, "h1"), (3, "h3"), (5, "h5"))):
        y = Y[:, hi]
        mask = y >= 0
        # movement mask: mid actually changes over horizon h
        mov = np.zeros(len(snaps), dtype=bool)
        for i in range(len(snaps) - h):
            mov[i] = snaps[i + h]["mid"] != snaps[i]["mid"]
        sel = mask & mov
        if sel.sum() < 200:
            print(f"{name}: too few movements ({int(sel.sum())}), skip"); continue
        Xm, ym = X[sel], y[sel].astype(int)
        n = len(Xm)
        cut = int(n * 0.70)
        Xtr, ytr = Xm[:cut], ym[:cut]
        Xte, yte = Xm[cut:], ym[cut:]
        if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
            print(f"{name}: degenerate target"); continue
        model = CatBoostClassifier(iterations=300, depth=4, learning_rate=0.05,
                                   loss_function="Logloss", eval_metric="AUC",
                                   random_seed=42, verbose=0)
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xte)[:, 1]
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(yte, p)
        # persistence baseline: same direction as last actual move
        idxs = sel.nonzero()[0]
        n_test = n - cut
        last_move = np.zeros(n_test)
        for i in range(n_test):
            j = idxs[cut + i]
            last_move[i] = 1.0 if snaps[j]["mid"] > snaps[max(0, j - 1)]["mid"] else 0.0
        base_acc = float((last_move == yte).mean())
        acc = float(((p >= 0.5).astype(int) == yte).mean())
        hit_up = float(yte[p >= 0.5].mean()) if (p >= 0.5).sum() else float("nan")
        hit_down = float((1 - yte)[p < 0.5].mean()) if (p < 0.5).sum() else float("nan")
        up_rate = float(yte.mean())
        print(f"{name}: AUC={auc:.4f} acc={acc:.3f} persistence={base_acc:.3f} "
              f"up_rate={up_rate:.3f} hit_up={hit_up:.3f} hit_down={hit_down:.3f} "
              f"n_mov_test={len(yte)} flat_share={1-mov[mask].mean():.2f}", flush=True)

    if args.gate:
        # gated MM comparison: quote ask only when signal says DOWN (avoid selling into rise)
        from mm_proto_backtest import run_gated_mm
        res = run_gated_mm(snaps, symbol=args.symbol, exchange=args.exchange)
        print(json.dumps(res, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
