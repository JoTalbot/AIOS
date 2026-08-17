#!/usr/bin/env python3
"""V2: verify microstructure signal on longer horizons (30s..15min) from ws data.

Uses snapshots_ws (1Hz-ish). Signal: OBI + microprice features at time t predict
direction of mid change over horizon H seconds ahead. Honest: only observations
where mid actually moves over H; time-split 70/30; CatBoost; AUC + hit rates.

Usage:
    python scripts/mm_signal_horizons.py [--min-rows 500]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np

DB = Path("/root/AIOS/data/quant/orderbooks.sqlite")


def load_ws(symbol: str) -> list[dict]:
    con = sqlite3.connect(DB)
    cur = con.execute(
        "SELECT ts, bid, ask, mid, spread_bps, bid_depth_usd, ask_depth_usd, "
        "bids_json, asks_json FROM snapshots_ws WHERE symbol=? ORDER BY ts",
        (symbol,))
    rows = cur.fetchall()
    con.close()
    import json
    out = []
    for r in rows:
        out.append({"ts": r[0], "bid": r[1], "ask": r[2], "mid": r[3],
                    "spread_bps": r[4], "bid_depth_usd": r[5], "ask_depth_usd": r[6],
                    "bids": json.loads(r[7]) if r[7] else [],
                    "asks": json.loads(r[8]) if r[8] else []})
    return out


def book_vol(levels, upto: int) -> float:
    return sum(q for _, q in levels[:upto])


def features(snaps: list[dict]) -> tuple[list[dict], np.ndarray]:
    n = len(snaps)
    mids = np.array([s["mid"] for s in snaps])
    F = []
    for i in range(n):
        s = snaps[i]
        bd1 = book_vol(s["bids"], 1)
        ad1 = book_vol(s["asks"], 1)
        bd5 = book_vol(s["bids"], 5)
        ad5 = book_vol(s["asks"], 5)
        obi1 = (bd1 - ad1) / (bd1 + ad1 + 1e-12)
        obi5 = (bd5 - ad5) / (bd5 + ad5 + 1e-12)
        micro = (s["ask"] * bd1 + s["bid"] * ad1) / (bd1 + ad1 + 1e-12)
        F.append({
            "obi1": obi1, "obi5": obi5,
            "micro_off": (micro - mids[i]) / mids[i] * 1e4 if mids[i] else 0.0,
            "spread_bps": (s["ask"] - s["bid"]) / mids[i] * 1e4 if mids[i] else 0.0,
            "ret1s": (mids[i] / mids[i - 1] - 1) * 1e4 if i > 0 and mids[i - 1] else 0.0,
        })
    return F, mids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-rows", type=int, default=400)
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    symbols = [r[0] for r in con.execute(
        "SELECT symbol, COUNT(*) c FROM snapshots_ws GROUP BY symbol HAVING c >= ?",
        (args.min_rows,))]
    con.close()
    print(f"symbols with >= {args.min_rows} ws rows: {symbols}", flush=True)

    from catboost import CatBoostClassifier
    from sklearn.metrics import roc_auc_score

    horizons = [30, 60, 180, 300, 900]
    for sym in symbols:
        snaps = load_ws(sym)
        if len(snaps) < args.min_rows:
            continue
        F, mids = features(snaps)
        feat_names = list(F[0].keys())
        X = np.array([[F[i][k] for k in feat_names] for i in range(len(F))])
        times = np.array([s["ts"] for s in snaps])
        print(f"\n=== {sym} ({len(snaps)} rows, span {(times[-1]-times[0])/60:.0f} мин) ===", flush=True)
        for H in horizons:
            # target: mid moves UP over next H seconds (by time, not row count)
            y = np.zeros(len(snaps))
            valid = np.zeros(len(snaps), dtype=bool)
            for i in range(len(snaps)):
                t_target = times[i] + H
                j = int(np.searchsorted(times, t_target, side="left"))
                if j < len(snaps):
                    valid[i] = True
                    y[i] = 1.0 if mids[j] > mids[i] else 0.0
            # движение: mid реально изменился
            sel = valid & (np.abs(np.array([mids[int(np.searchsorted(times, times[i]+H, side='left'))] if i < len(snaps) else mids[-1] for i in range(len(snaps))]) - mids) > 0) if False else valid
            # движение: mid на горизонте отличается
            mov = np.zeros(len(snaps), dtype=bool)
            for i in range(len(snaps)):
                j = int(np.searchsorted(times, times[i] + H, side="left"))
                if j < len(snaps):
                    mov[i] = mids[j] != mids[i]
            sel = valid & mov
            if sel.sum() < 150:
                continue
            idxs = sel.nonzero()[0]
            cut = int(len(idxs) * 0.70)
            tr, te = idxs[:cut], idxs[cut:]
            if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
                print(f"  H={H:>4}s: degenerate", flush=True)
                continue
            m = CatBoostClassifier(iterations=200, depth=4, learning_rate=0.05,
                                   loss_function="Logloss", eval_metric="AUC",
                                   random_seed=42, verbose=0)
            m.fit(X[tr], y[tr].astype(int))
            p = m.predict_proba(X[te])[:, 1]
            auc = roc_auc_score(y[te], p)
            hit_up = float(y[te][p >= 0.5].mean()) if (p >= 0.5).sum() else float("nan")
            hit_dn = float((1 - y[te])[p < 0.5].mean()) if (p < 0.5).sum() else float("nan")
            print(f"  H={H:>4}s: AUC={auc:.3f} hit↑={hit_up:.2f} hit↓={hit_dn:.2f} "
                  f"n={len(te)} up_rate={y[te].mean():.2f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
