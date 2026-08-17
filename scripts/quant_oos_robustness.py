#!/usr/bin/env python3
"""Robustness checks for the N1 (trail=1.0) OOS finding.

1. Jackknife over symbols: drop each symbol in turn, recompute unique-trade PnL for
   BASE (trail 0.988) vs N1 (trail 1.0) on the fold-0.70 OOS window. If the positive
   edge depends on a single symbol, jackknife will show it.
2. Venue robustness: same signals (ML>=0.65), but prices taken from binance series
   (where available) instead of allowlist — N1 vs BASE on the same calendar window.

One CatBoost v2 is trained on the fold-0.70 train segment (allowlist data) and reused
for both checks; ML threshold is the fixed deployed 0.65 to mirror the engine.

Usage:
    python scripts/quant_oos_robustness.py [--output data/reports/oos_robustness.md]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quant_monthly_backtest as qmb
from quant_oos_profit_experiments import (
    ML_PARAMS,
    GAP_BARS,
    _atr14,
    metrics,
    simulate,
)

STAKE = 200.0

# Reuse the same variant dicts as the OOS experiment (a-priori definitions).
BASE_V = {}
N1_V = {"trail": 1.0}


def load_series(venue: str = "allowlist") -> dict[str, dict]:
    symbols, _venue = qmb.load_symbols(venue)
    out: dict[str, dict] = {}
    for sym, df in symbols.items():
        if len(df) < 1500:
            continue
        df = df.reset_index(drop=True)
        feats = qmb._compute_features(df)
        out[sym] = {
            "df": df,
            "feats": feats,
            "sma50": df["close"].rolling(50).mean().values,
            "sma100": df["close"].rolling(100).mean().values,
            "sma150": df["close"].rolling(150).mean().values,
            "sma200": df["close"].rolling(200).mean().values,
            "atr14": _atr14(df),
            "closes": df["close"].values,
            "highs": df["high"].values,
            "lows": df["low"].values,
            "times": df["timestamp_ms"].values,
        }
    return out


def train_fold(series: dict[str, dict], train_frac: float = 0.70):
    from catboost import CatBoostClassifier

    rows: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for sym, s in series.items():
        df = s["df"]
        closes = df["close"].values
        target = (np.roll(closes, -1) > closes).astype(int)
        target[-1] = 0
        cut = int(len(df) * train_frac)
        X = s["feats"][qmb.FEATURES].values[: cut - GAP_BARS].astype(np.float64)
        y = target[: cut - GAP_BARS]
        ok = ~np.isnan(X).any(axis=1)
        rows.append(X[ok])
        ys.append(y[ok])
    X_all = np.vstack(rows)
    y_all = np.concatenate(ys)
    model = CatBoostClassifier(**ML_PARAMS)
    model.fit(X_all, y_all)
    return model


def predict_all(series: dict[str, dict], model, train_frac: float = 0.70) -> dict[str, dict]:
    out = {}
    for sym, s in series.items():
        cut = int(len(s["df"]) * train_frac)
        X = s["feats"][qmb.FEATURES].values.astype(np.float64)
        p = model.predict_proba(X)[:, 1]
        arr = np.full(len(X), np.nan)
        arr[cut:] = p[cut:]
        s2 = dict(s)
        s2["probs"] = arr
        out[sym] = s2
    return out


def unique_pnl(trades: list[dict]) -> float:
    seen: set[tuple] = set()
    total = 0.0
    for t in trades:
        key = (t["symbol"], t["opened_at"])
        if key in seen:
            continue
        seen.add(key)
        total += t["net"]
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=Path("data/reports/oos_robustness.md"))
    args = ap.parse_args()

    series = load_series("allowlist")
    print(f"allowlist symbols: {len(series)}", flush=True)
    model = train_fold(series, 0.70)
    series = predict_all(series, model, 0.70)

    # baseline on fold-0.70 window
    def trades_for(variant: dict) -> list[dict]:
        tr = []
        for sym, s in series.items():
            cut = int(len(s["df"]) * 0.70)
            tr.extend(simulate(sym, s, variant, cut, 0.65))
        return tr

    base_trades = trades_for(BASE_V)
    n1_trades = trades_for(N1_V)
    base_pnl = unique_pnl(base_trades)
    n1_pnl = unique_pnl(n1_trades)
    print(f"baseline fold-0.70: BASE {base_pnl:+.2f}$  N1 {n1_pnl:+.2f}$", flush=True)

    # --- jackknife ---
    rows = []
    for sym in sorted(series):
        sub = {k: v for k, v in series.items() if k != sym}
        bt, nt = [], []
        for name2, s2 in sub.items():
            cut = int(len(s2["df"]) * 0.70)
            bt.extend(simulate(name2, s2, BASE_V, cut, 0.65))
            nt.extend(simulate(name2, s2, N1_V, cut, 0.65))
        b = unique_pnl(bt)
        n = unique_pnl(nt)
        rows.append((sym, b, n))
        print(f"jackknife -{sym}: BASE {b:+.2f}$ N1 {n:+.2f}$", flush=True)

    jb = [r[1] for r in rows]
    jn = [r[2] for r in rows]
    md = ["# Устойчивость N1 (trail=1.0): jackknife по символам + binance-цены", "",
          "Окно: fold 0.70 (test-хвост каждого символа),",
          "уникальные сделки (дедуп), ставка $200, ML>=0.65 (фикс. порог прод-движка).",
          "",
          f"Baseline: BASE {base_pnl:+.2f}$ | N1 {n1_pnl:+.2f}$",
          "",
          "| Без символа | BASE $ | N1 $ |",
          "|---|---:|---:|"]
    for sym, b, n in rows:
        md.append(f"| -{sym} | {b:+.2f} | {n:+.2f} |")
    md += ["",
           f"Jackknife BASE: min {min(jb):+.2f} / max {max(jb):+.2f} / med {statistics.median(jb):+.2f}",
           f"Jackknife N1:   min {min(jn):+.2f} / max {max(jn):+.2f} / med {statistics.median(jn):+.2f}"]

    # --- binance venue check ---
    md += ["", "## Проверка на binance-ценах (тот же календарный OOS-период)", ""]
    bin_series = load_series("binance")
    if bin_series:
        bin_series = predict_all(bin_series, model, 0.70)
        bt2, nt2 = [], []
        for name2, s2 in bin_series.items():
            cut = int(len(s2["df"]) * 0.70)
            bt2.extend(simulate(name2, s2, BASE_V, cut, 0.65))
            nt2.extend(simulate(name2, s2, N1_V, cut, 0.65))
        bp = unique_pnl(bt2)
        np2 = unique_pnl(nt2)
        md += [f"binance-символов: {len(bin_series)}",
               f"BASE: {bp:+.2f}$ | N1: {np2:+.2f}$",
               "",
               "| Сделка (N1, binance) | PnL $ | reason |",
               "|---|---:|---|"]
        seen = set()
        for t in sorted(nt2, key=lambda x: x["opened_at"]):
            key = (t["symbol"], t["opened_at"])
            if key in seen:
                continue
            seen.add(key)
            d = datetime.fromtimestamp(t["opened_at"] / 1000, tz=UTC).strftime("%m-%d %H:%M")
            md.append(f"| {d} {t['symbol']} | {t['net']:+.2f} | {t['reason']} |")
        print(f"binance: BASE {bp:+.2f}$ N1 {np2:+.2f}$", flush=True)
    else:
        md += ["binance-серии недоступны"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
