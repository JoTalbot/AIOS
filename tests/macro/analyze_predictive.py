#!/usr/bin/env python3
"""Predictive-power analysis: do macro/on-chain/derivatives series predict BTC?

Builds a merged dataset (daily and hourly), computes LAGGED features
(feature at t-1 -> BTC return at t), then:
  - Pearson correlation of each feature with forward returns (1d / 24h);
  - event test: top-quintile vs bottom-quintile of feature -> average forward
    return difference (robust to noise);
  - honest note: correlations on overlapping windows are indicative, not proof.

Usage:
    python analyze_predictive.py [--data-dir data/market_data] [--deriv data/derivatives]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def load_series(path: Path, gran: str = "day") -> dict[int, float]:
    out = {}
    if not path.exists():
        return out
    bucket = 3600 if gran == "hour" else 86400
    for line in path.read_text().splitlines():
        try:
            r = json.loads(line)
            # normalize to the bucket start (UTC midnight for day, top of the
            # hour for hour) so series with different close times align
            out[(int(r["ts"]) // bucket) * bucket] = float(r["value"])
        except Exception:
            continue
    return out


def load_deriv(path: Path, key: str) -> dict[int, float]:
    out = {}
    if not path.exists():
        return out
    rows = json.loads(path.read_text())
    if key == "klines":
        for r in rows:
            out[int(r["open_ts"]) // 1000] = r["taker_buy_ratio"]
    elif key in ("global_lsr", "top_lsr"):
        for r in rows:
            out[int(r["ts"]) // 1000] = r["lsr"]
    elif key == "oi":
        for r in rows:
            out[int(r["ts"]) // 1000] = r["oi"]
    return out


def align(feature: dict[int, float], target: dict[int, float], lag_hours: int,
          step_hours: int) -> tuple[np.ndarray, np.ndarray]:
    """feature at t-lag vs target return over [t, t+step]."""
    xs, ys = [], []
    for t in sorted(feature):
        tt = t + lag_hours * 3600
        t2 = tt + step_hours * 3600
        if tt in target and t2 in target and target[tt] > 0:
            ret = (target[t2] / target[tt] - 1.0) * 100.0
            xs.append(feature[t])
            ys.append(ret)
    return np.array(xs), np.array(ys)


def eval_feature(name: str, feat: dict[int, float], price: dict[int, float],
                 lag_h: int, step_h: int, min_n: int = 30):
    x, y = align(feat, price, lag_h, step_h)
    if len(x) < min_n:
        print(f"  {name:<18} lag{lag_h}h step{step_h}h: n={len(x)} (мало)")
        return None
    corr = float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 0 and np.std(y) > 0 else 0.0
    # квинтильный тест
    q20, q80 = np.percentile(x, 20), np.percentile(x, 80)
    lo = y[x <= q20].mean() if (x <= q20).any() else float("nan")
    hi = y[x >= q80].mean() if (x >= q80).any() else float("nan")
    diff = hi - lo if not (np.isnan(hi) or np.isnan(lo)) else float("nan")
    star = " ***" if abs(corr) > 0.15 else (" **" if abs(corr) > 0.10 else "")
    print(f"  {name:<18} lag{lag_h}h step{step_h}h: n={len(x):>4} corr={corr:+.3f}{star} "
          f"Q20={lo:+.3f}% Q80={hi:+.3f}% diff={diff:+.3f}%")
    return {"name": name, "corr": corr, "diff": diff, "n": len(x)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("data/market_data"))
    ap.add_argument("--deriv", type=Path, default=Path("data/derivatives"))
    args = ap.parse_args()

    price = load_series(args.data_dir / "BTC_USD.jsonl")
    print(f"BTC_USD: {len(price)} дней", flush=True)

    # --- daily macro/on-chain: lag 1d, step 1d ---
    print("\n=== Daily: фича (t-1) -> BTC ret (t..t+1d) ===")
    daily_feats = {
        "DXY": load_series(args.data_dir / "DXY.jsonl"),
        "SPX": load_series(args.data_dir / "SPX.jsonl"),
        "NDX": load_series(args.data_dir / "NDX.jsonl"),
        "IBIT": load_series(args.data_dir / "IBIT.jsonl"),
        "hashrate": load_series(args.data_dir / "hashrate.jsonl"),
        "n_tx": load_series(args.data_dir / "n_tx.jsonl"),
        "n_unique_addr": load_series(args.data_dir / "n_unique_addr.jsonl"),
        "tx_vol_usd": load_series(args.data_dir / "tx_vol_usd.jsonl"),
    }
    for name, f in daily_feats.items():
        eval_feature(name, f, price, lag_h=24, step_h=24)

    # --- hourly derivatives: lag 1h, step 1h / 4h / 24h ---
    print("\n=== Hourly (деривативы): фича (t-1) -> BTC ret ===")
    der_feats = {
        "taker_buy_ratio": load_deriv(args.deriv / "BTC_klines.json", "klines"),
        "global_lsr": load_deriv(args.deriv / "BTC_global_lsr.json", "global_lsr"),
        "top_lsr": load_deriv(args.deriv / "BTC_top_lsr.json", "top_lsr"),
        "oi": load_deriv(args.deriv / "BTC_oi.json", "oi"),
    }
    hprice = load_series(args.data_dir / "BTC_USD_1h.jsonl") if (args.data_dir / "BTC_USD_1h.jsonl").exists() else {}
    print(f"  (часовой BTC: {len(hprice)} баров)", flush=True)
    for name, f in der_feats.items():
        if not hprice:
            print(f"  {name}: нет часовых цен")
            continue
        for step in (1, 4, 24):
            eval_feature(name, f, hprice, lag_h=1, step_h=step, min_n=50)

    print("\n=== Интерпретация ===")
    print("corr |>0.10| — слабый сигнал; |>0.15| — заметный; diff>0.3% — квинтильный спред.")
    print("Корреляции лаговых фич с будущей доходностью — это и есть предсказательная проверка.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
