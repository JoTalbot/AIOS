#!/usr/bin/env python3
"""Strict OOS check of the BTC long-horizon orderbook signal (MM interim-2).

Hypothesis (scripts/mm_signal_horizons.py, 2026-08-17): 1Hz orderbook features
(OBI/microprice) predict BTC mid direction over 180-900s with AUC 0.63-0.66.
That run used overlapping observation windows and no purge gap, so its
long-horizon AUC may be inflated by label leakage across the train/test split.

This check is deliberately stricter:
- PURGE split: training observations must close (t+H) before the test period
  starts; test observations begin only after the split time.
- STRIDE: test observations are sampled every max(1, H//4) seconds to reduce
  pseudo-replication from overlapping label windows.
- Feature attribution: orderbook features vs momentum lags vs full set.
- Strategy: long when prob_up >= q90(train), exit after H, net of the
  Directional-v2 round-trip cost (0.5%).

Read-only research; never trades.

Usage:
    python scripts/mm_signal_long_horizon_check.py [--symbol BTC]
        [--out data/reports/btc_long_horizon_signal.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DB = REPO_ROOT / "data" / "quant" / "orderbooks.sqlite"
COST = 0.005  # Directional-v2 round trip: 200*(fee 0.0015 + spread 0.0005 + slip 0.0005)
HORIZONS = [60, 180, 300, 600, 900]
MOMENTUM_LAGS = [60, 180, 300, 600]

ORDERBOOK_FEATURES = ["obi1", "obi5", "micro_off", "spread_bps", "ret1s"]
MOMENTUM_FEATURES = [f"mom{k}" for k in MOMENTUM_LAGS]


# ---------------------------------------------------------------- pure parts --
def book_vol(levels, upto: int) -> float:
    return sum(q for _, q in levels[:upto])


def _momenta(mids: np.ndarray, lags: list[int]) -> dict[str, np.ndarray]:
    out = {}
    for k in lags:
        with np.errstate(divide="ignore", invalid="ignore"):
            m = np.full(len(mids), np.nan)
            m[k:] = mids[k:] / mids[:-k] - 1.0
        m[~np.isfinite(m)] = 0.0
        out[f"mom{k}"] = m * 1e4
    return out


def _labels(mids: np.ndarray, times: np.ndarray, H: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """valid[i], mov[i], y[i] for 'mid moves UP over next H seconds'."""

    n = len(times)
    valid = np.zeros(n, dtype=bool)
    mov = np.zeros(n, dtype=bool)
    y = np.zeros(n)
    for i in range(n):
        j = int(np.searchsorted(times, times[i] + H, side="left"))
        if j >= n:
            continue
        valid[i] = True
        if mids[j] != mids[i]:
            mov[i] = True
            y[i] = 1.0 if mids[j] > mids[i] else 0.0
    return valid, mov, y


def purge_split(times: np.ndarray, valid: np.ndarray, mov: np.ndarray,
                H: int, split_t: float, stride: int) -> tuple[np.ndarray, np.ndarray]:
    """Train observations close before split_t; test starts at split_t with stride."""

    tr = np.nonzero(valid & mov & (times + H < split_t))[0]
    te = np.nonzero(valid & mov & (times >= split_t))[0]
    if stride > 1 and len(te) > 0:
        te = te[::stride]
    return tr, te


def bootstrap_auc(y: np.ndarray, p: np.ndarray, n_boot: int = 200, seed: int = 42) -> tuple[float, float]:
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(seed)
    aucs = []
    idx = np.arange(len(y))
    for _ in range(n_boot):
        s = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[s])) < 2:
            continue
        aucs.append(roc_auc_score(y[s], p[s]))
    return float(np.mean(aucs)), float(np.std(aucs))


# ------------------------------------------------------------------- loader --
def load_snaps(symbol: str) -> list[dict]:
    con = sqlite3.connect(DB, timeout=30)
    cur = con.execute(
        "SELECT ts, bid, ask, mid, spread_bps, bid_depth_usd, ask_depth_usd, "
        "bids_json, asks_json FROM snapshots_ws WHERE symbol=? ORDER BY ts", (symbol,))
    out = []
    for r in cur:
        out.append({"ts": r[0], "bid": r[1], "ask": r[2], "mid": r[3],
                    "spread_bps": r[4], "bid_depth_usd": r[5], "ask_depth_usd": r[6],
                    "bids": json.loads(r[7]) if r[7] else [],
                    "asks": json.loads(r[8]) if r[8] else []})
    con.close()
    return out


def build_features(snaps: list[dict]) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    n = len(snaps)
    mids = np.array([s["mid"] for s in snaps], dtype=float)
    times = np.array([s["ts"] for s in snaps], dtype=float)
    obi1 = np.zeros(n)
    obi5 = np.zeros(n)
    micro_off = np.zeros(n)
    spread = np.zeros(n)
    ret1s = np.zeros(n)
    for i, s in enumerate(snaps):
        bd1 = book_vol(s["bids"], 1)
        ad1 = book_vol(s["asks"], 1)
        bd5 = book_vol(s["bids"], 5)
        ad5 = book_vol(s["asks"], 5)
        obi1[i] = (bd1 - ad1) / (bd1 + ad1 + 1e-12)
        obi5[i] = (bd5 - ad5) / (bd5 + ad5 + 1e-12)
        micro = (s["ask"] * bd1 + s["bid"] * ad1) / (bd1 + ad1 + 1e-12)
        micro_off[i] = (micro - mids[i]) / mids[i] * 1e4 if mids[i] else 0.0
        spread[i] = s["spread_bps"]
        if i > 0 and mids[i - 1]:
            ret1s[i] = (mids[i] / mids[i - 1] - 1) * 1e4
    F = {"obi1": obi1, "obi5": obi5, "micro_off": micro_off,
         "spread_bps": spread, "ret1s": ret1s}
    F.update(_momenta(mids, MOMENTUM_LAGS))
    return F, mids, times


# ---------------------------------------------------------------------- main --
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "data" / "reports" / "btc_long_horizon_signal.json")
    args = ap.parse_args()

    from catboost import CatBoostClassifier
    from sklearn.metrics import roc_auc_score

    snaps = load_snaps(args.symbol)
    if len(snaps) < 2000:
        print(f"not enough data: {len(snaps)}")
        return 1
    F, mids, times = build_features(snaps)
    feat_names = list(F.keys())
    X = np.array([[F[k][i] for k in feat_names] for i in range(len(snaps))])
    span_s = float(times[-1] - times[0])
    split_t = float(times[0]) + 0.70 * span_s

    report = {"symbol": args.symbol, "n_snapshots": len(snaps),
              "span_h": round(span_s / 3600, 1), "split_t": split_t,
              "cost_round_trip": COST, "horizons": {}}
    print(f"{args.symbol}: {len(snaps)} snaps, span {span_s/3600:.1f}h", flush=True)

    for H in HORIZONS:
        valid, mov, y = _labels(mids, times, H)
        stride = max(1, H // 4)
        tr, te = purge_split(times, valid, mov, H, split_t, stride)
        if len(tr) < 500 or len(te) < 100 or len(np.unique(y[tr])) < 2:
            print(f"  H={H}s: degenerate (tr={len(tr)} te={len(te)})", flush=True)
            continue
        row = {"n_train": int(len(tr)), "n_test": int(len(te)),
               "up_rate_test": round(float(y[te].mean()), 3), "stride": stride}
        models = {}
        for name, feats in (("orderbook", ORDERBOOK_FEATURES), ("momentum", MOMENTUM_FEATURES),
                            ("full", ORDERBOOK_FEATURES + MOMENTUM_FEATURES)):
            cols = [feat_names.index(f) for f in feats]
            m = CatBoostClassifier(iterations=200, depth=4, learning_rate=0.05,
                                   loss_function="Logloss", eval_metric="AUC",
                                   random_seed=42, verbose=0)
            m.fit(X[tr][:, cols], y[tr].astype(int))
            p = m.predict_proba(X[te][:, cols])[:, 1]
            auc = float(roc_auc_score(y[te], p))
            auc_mean, auc_std = bootstrap_auc(y[te], p)
            row[name + "_auc"] = round(auc, 3)
            row[name + "_auc_boot_std"] = round(auc_std, 3)
            models[name] = p
        # strategy on the full set: long when p >= q90(train), exit after H, net of cost
        p_full = models["full"]
        p_tr = None
        cols = [feat_names.index(f) for f in ORDERBOOK_FEATURES + MOMENTUM_FEATURES]
        m_tmp = CatBoostClassifier(iterations=200, depth=4, learning_rate=0.05,
                                   loss_function="Logloss", eval_metric="AUC",
                                   random_seed=42, verbose=0)
        m_tmp.fit(X[tr][:, cols], y[tr].astype(int))
        p_tr = m_tmp.predict_proba(X[tr][:, cols])[:, 1]
        thr = float(np.quantile(p_tr, 0.90))
        j_idx = np.array([int(np.searchsorted(times, times[i] + H, side="left")) for i in te])
        rets = mids[j_idx] / mids[te] - 1.0
        sel = p_full >= thr
        row["threshold_q90_train"] = round(thr, 3)
        row["n_long"] = int(sel.sum())
        if sel.sum():
            row["long_mean_ret_pct"] = round(float(np.mean(rets[sel] - COST)) * 100, 3)
            row["long_positive_pct"] = round(float(np.mean(rets[sel] - COST > 0)) * 100, 1)
        row["baseline_mean_ret_pct"] = round(float(np.mean(rets - COST)) * 100, 3)
        row["baseline_positive_pct"] = round(float(np.mean(rets - COST > 0)) * 100, 1)
        report["horizons"][str(H)] = row
        print(f"  H={H:>4}s: n_tr={len(tr)} n_te={len(te)} | AUC ob={row['orderbook_auc']:.3f} "
              f"mom={row['momentum_auc']:.3f} full={row['full_auc']:.3f} | "
              f"long {row.get('n_long', 0)} trades ret={row.get('long_mean_ret_pct', float('nan'))}% "
              f"vs base {row['baseline_mean_ret_pct']}%", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"report -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
