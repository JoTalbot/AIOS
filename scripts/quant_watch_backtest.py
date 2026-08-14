#!/usr/bin/env python3
"""Historical verification of the Quant Signal Monitor WATCH rules.

Replays the signal-product logic (regime + ML prob thresholds) over the OOS
tail of each symbol and measures how often WATCH_UP/WATCH_DOWN are confirmed
by the next-bar direction. Read-only; no orders, no state mutation.

Usage:
    python scripts/quant_watch_backtest.py [--oos-frac 0.30]
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUANT_DIR = REPO_ROOT / "data" / "quant"
MODELS_DIR = QUANT_DIR / "models"

sys.path.insert(0, str(REPO_ROOT))
from aios_core.quant_regime_v3 import compute_regime_features  # noqa: E402

FEATURES = [
    "ret1", "ret3", "ret6", "ret12", "ret24",
    "rsi", "bb_pos", "macd_norm", "ema_gap",
    "vol_ratio", "vol_z", "bar_range_pct", "hl_pos",
]

WATCH_UP_RULES = {"prob_min": 0.60, "regime": "trend_up"}
WATCH_DOWN_RULES = {"prob_max": 0.40, "regime": "trend_down"}


def _features(df: pd.DataFrame) -> pd.DataFrame:
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
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oos-frac", type=float, default=0.30)
    args = parser.parse_args()

    from catboost import CatBoostClassifier

    model = CatBoostClassifier()
    model.load_model(str(MODELS_DIR / "catboost_price_dir_v2.cbm"))

    results = []
    total_up = total_down = conf_up = conf_down = 0
    for path in sorted(glob.glob(str(QUANT_DIR / "*" / "binance" / "*_1h.csv"))):
        symbol = Path(path).stem.split("_")[0]
        df = pd.read_csv(path).sort_values("timestamp_ms")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])
        g = _features(df)
        clean = g.dropna(subset=FEATURES).reset_index(drop=True)
        if len(clean) < 300:
            continue
        cut = int(len(clean) * (1.0 - args.oos_frac))
        oos = clean.iloc[cut:].reset_index(drop=True)

        # Regime per bar (same code path as the signal product).
        rows = [
            {
                "timestamp": float(r.timestamp_ms),
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume),
            }
            for r in oos.itertuples()
        ]
        regimes = compute_regime_features(rows)
        probs = model.predict_proba(oos[FEATURES].values.astype(np.float64))[:, 1]

        n_up = n_down = hit_up = hit_down = 0
        for i in range(len(oos) - 1):
            regime = regimes[i]["regime"]
            p = probs[i]
            nxt_dir = 1 if oos["close"].iloc[i + 1] > oos["close"].iloc[i] else 0
            if regime == WATCH_UP_RULES["regime"] and p >= WATCH_UP_RULES["prob_min"]:
                n_up += 1
                hit_up += nxt_dir
            if regime == WATCH_DOWN_RULES["regime"] and p <= WATCH_DOWN_RULES["prob_max"]:
                n_down += 1
                hit_down += 1 - nxt_dir
        results.append(
            {
                "symbol": symbol,
                "bars_oos": len(oos),
                "watch_up": n_up,
                "watch_up_hit": hit_up,
                "watch_down": n_down,
                "watch_down_hit": hit_down,
            }
        )
        total_up += n_up
        conf_up += hit_up
        total_down += n_down
        conf_down += hit_down

    report = {
        "oos_frac": args.oos_frac,
        "watch_up": {
            "signals": total_up,
            "confirmed": conf_up,
            "precision": round(conf_up / total_up, 4) if total_up else None,
        },
        "watch_down": {
            "signals": total_down,
            "confirmed": conf_down,
            "precision": round(conf_down / total_down, 4) if total_down else None,
        },
        "per_symbol": results,
    }
    out = REPO_ROOT / "data" / "reports" / "quant_watch_backtest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "per_symbol"}, ensure_ascii=False, indent=2))
    print("watch_up symbols:", sum(1 for r in results if r["watch_up"]),
          "| watch_down symbols:", sum(1 for r in results if r["watch_down"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
