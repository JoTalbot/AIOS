#!/usr/bin/env python3
"""Multi-horizon label experiment for the quant direction model.

The deployed model predicts next-1h direction, but Directional v2 exits hold
positions up to 72 bars (TP+2%/SL-1%). This experiment trains the same 13
scale-free features on horizons h = 1, 4, 8, 24 bars and compares OOS
discrimination (AUC, hit@0.60/0.65). Read-only.

Usage:
    python scripts/quant_ml_horizon_experiment.py
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUANT_DIR = REPO_ROOT / "data" / "quant"

FEATURES = [
    "ret1", "ret3", "ret6", "ret12", "ret24",
    "rsi", "bb_pos", "macd_norm", "ema_gap",
    "vol_ratio", "vol_z", "bar_range_pct", "hl_pos",
]
HORIZONS = (1, 4, 8, 24)
TRAIN_FRAC = 0.70
GAP_BARS = 48


def _compute(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    g = df.copy()
    g["ret1"] = g["close"].pct_change()
    g["ret3"] = g["close"].pct_change(3)
    g["ret6"] = g["close"].pct_change(6)
    g["ret12"] = g["close"].pct_change(12)
    g["ret24"] = g["close"].pct_change(24)
    g["ema12"] = g["close"].ewm(span=12).mean()
    g["ema26"] = g["close"].ewm(span=26).mean()
    chg = g["close"].pct_change()
    up = chg.clip(lower=0).rolling(14).mean()
    down = (-chg.clip(upper=0)).rolling(14).mean()
    g["rsi"] = 100.0 - 100.0 / (1.0 + up / down.replace(0, 1e-9))
    bb_mid = g["close"].rolling(20).mean()
    bb_std = g["close"].rolling(20).std()
    g["bb_pos"] = ((g["close"] - bb_mid + 2 * bb_std) / (4 * bb_std).replace(0, np.nan)).clip(0, 1)
    macd = g["ema12"] - g["ema26"]
    g["macd_norm"] = macd / g["close"]
    g["ema_gap"] = (g["ema12"] - g["ema26"]) / g["close"]
    vol_mean = g["volume"].rolling(20).mean()
    vol_std = g["volume"].rolling(20).std()
    g["vol_ratio"] = g["volume"] / vol_mean.replace(0, np.nan)
    g["vol_z"] = (g["volume"] - vol_mean) / vol_std.replace(0, np.nan)
    g["bar_range_pct"] = (g["high"] - g["low"]) / g["close"]
    g["hl_pos"] = (g["close"] - g["low"]) / (g["high"] - g["low"]).replace(0, np.nan)
    # Horizon label: close[t+h] > close[t] (h bars ahead, no overlap with exit rule)
    g["target"] = (g["close"].shift(-horizon) > g["close"]).astype(int)
    return g


def _split(g: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    clean = g.dropna(subset=FEATURES + ["target"]).reset_index(drop=True)
    cut = int(len(clean) * TRAIN_FRAC)
    return clean.iloc[: cut - GAP_BARS], clean.iloc[cut:]


def main() -> int:
    from catboost import CatBoostClassifier
    from sklearn.metrics import roc_auc_score

    report = {}
    for horizon in HORIZONS:
        frames = []
        for path in sorted(glob.glob(str(QUANT_DIR / "*" / "binance" / "*_1h.csv"))):
            df = pd.read_csv(path).sort_values("timestamp_ms")
            df = df.dropna(subset=["open", "high", "low", "close", "volume"])
            g = _compute(df, horizon)
            if len(g.dropna(subset=FEATURES + ["target"])) < 150:
                continue
            frames.append(g)
        trains, tests = [], []
        for g in frames:
            tr, te = _split(g)
            if len(tr) > 100 and len(te) > 50:
                trains.append(tr)
                tests.append(te)
        df_tr = pd.concat(trains, ignore_index=True)
        df_te = pd.concat(tests, ignore_index=True)
        model = CatBoostClassifier(
            iterations=400, depth=5, learning_rate=0.03, l2_leaf_reg=5.0,
            loss_function="Logloss", eval_metric="AUC", random_seed=42,
            verbose=0, thread_count=-1,
        )
        model.fit(df_tr[FEATURES].values.astype(np.float64), df_tr["target"].values.astype(int))
        y = df_te["target"].values.astype(int)
        p = model.predict_proba(df_te[FEATURES].values.astype(np.float64))[:, 1]
        entry = {
            "train_rows": int(len(df_tr)),
            "test_rows": int(len(df_te)),
            "up_rate": round(float(y.mean()), 4),
            "auc": round(float(roc_auc_score(y, p)), 4) if len(np.unique(y)) > 1 else None,
        }
        for thr in (0.60, 0.65):
            mask = p >= thr
            entry[f"cov_{int(thr * 100):03d}"] = round(float(mask.mean()), 5)
            if mask.sum() > 0:
                entry[f"hit_{int(thr * 100):03d}"] = round(float(y[mask].mean()), 4)
            else:
                entry[f"hit_{int(thr * 100):03d}"] = None
        report[f"h{horizon}"] = entry
        print(f"h{horizon}: {json.dumps(entry, ensure_ascii=False)}", flush=True)

    out = REPO_ROOT / "data" / "reports" / "quant_ml_horizon_experiment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("report ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
