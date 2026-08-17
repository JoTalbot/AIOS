#!/usr/bin/env python3
"""Timeframe & universe experiment: does 4h or a top-liquidity universe produce edge?

Honest walk-forward comparison on the SAME calendar test window (~last 3.5 months):
- series resampled 1h -> 4h (no lookahead: aggregates of closed bars);
- a FRESH CatBoost v2 is trained per timeframe on the first 70% of each symbol's
  history (gap 48 bars), predictions on the untouched 30% tail;
- engine run 1:1 (reuses run_backtest from quant_prod_3m_backtest) with the SAME
  config as the live unit (trail=1.0, TP2%/SL1%, ML>=0.65, conf>=0.88, kill 0.25%);
- variants: timeframe (1h/4h) x universe (all 33 / top-12 by USD volume) x RL veto
  (on/off). Top-12 chosen a-priori by last-30d USD volume (volume*close).

Usage:
    python scripts/quant_tf_universe_experiment.py [--output data/reports/tf_universe_experiment.md]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quant_monthly_backtest as qmb
from quant_ml_eval_train import GAP_BARS
from quant_prod_3m_backtest import (
    build_config,
    load_unit_env,
    run_backtest,
    summarize,
)

ML_PARAMS = dict(iterations=400, depth=5, learning_rate=0.03, l2_leaf_reg=5.0,
                 loss_function="Logloss", eval_metric="AUC", random_seed=42,
                 verbose=0, thread_count=-1)


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample 1h OHLCV to a higher timeframe (rule like '4h')."""
    g = df.copy()
    g["dt"] = pd.to_datetime(g["timestamp_ms"], unit="ms", utc=True)
    g = g.set_index("dt").sort_index()
    agg = g.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                "close": "last", "volume": "sum"})
    agg = agg.dropna(subset=["open", "high", "low", "close"]).reset_index()
    # dtype is datetime64[ms, UTC] -> astype(int64) already yields milliseconds
    agg["timestamp_ms"] = agg["dt"].astype("int64")
    return agg[["timestamp_ms", "open", "high", "low", "close", "volume"]]


def build_series(env: dict, universe: set[str] | None, rule: str) -> dict[str, dict]:
    """Series keyed 'ex:sym' for the given timeframe; universe filter optional."""
    from quant_prod_3m_backtest import load_series as load_1h_series

    all_series, _used = load_1h_series(env)
    out: dict[str, dict] = {}
    for key, s in all_series.items():
        sym = s["symbol"]
        if universe is not None and sym not in universe:
            continue
        if rule == "1h":
            df = s["df"]
        else:
            df = resample(s["df"], rule)
        if len(df) < 600:
            continue
        feats = qmb._compute_features(df)
        out[key] = {
            "symbol": sym,
            "exchange": s["exchange"],
            "df": df.reset_index(drop=True),
            "feats": feats.reset_index(drop=True),
            "closes": df["close"].values,
            "highs": df["high"].values,
            "lows": df["low"].values,
            "times": df["timestamp_ms"].values,
        }
    return out


def train_and_predict(series: dict[str, dict], train_frac: float = 0.70) -> dict[str, np.ndarray]:
    from catboost import CatBoostClassifier

    rows: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    cuts: dict[str, int] = {}
    for key, s in series.items():
        closes = s["closes"]
        target = (np.roll(closes, -1) > closes).astype(int)
        target[-1] = 0
        cut = int(len(closes) * train_frac)
        cuts[key] = cut
        X = s["feats"][qmb.FEATURES].values[: cut - GAP_BARS].astype(np.float64)
        y = target[: cut - GAP_BARS]
        ok = ~np.isnan(X).any(axis=1)
        rows.append(X[ok])
        ys.append(y[ok])
    X_all = np.vstack(rows)
    y_all = np.concatenate(ys)
    print(f"  train rows={len(X_all)}", flush=True)
    model = CatBoostClassifier(**ML_PARAMS)
    model.fit(X_all, y_all)
    probs: dict[str, np.ndarray] = {}
    for key, s in series.items():
        X = s["feats"][qmb.FEATURES].values.astype(np.float64)
        p = model.predict_proba(X)[:, 1]
        arr = np.full(len(X), np.nan)
        arr[cuts[key]:] = p[cuts[key]:]
        probs[key] = arr
    return probs


def top_universe(series: dict[str, dict], n: int = 12, days: int = 30) -> set[str]:
    """Top-n symbols by average USD volume (volume*close) over the last `days` days."""
    usd_vol: dict[str, float] = {}
    for key, s in series.items():
        df = s["df"].tail(days * 24)
        v = float((df["volume"] * df["close"]).mean())
        usd_vol[s["symbol"]] = max(usd_vol.get(s["symbol"], 0.0), v)
    top = [sym for sym, _ in sorted(usd_vol.items(), key=lambda x: -x[1])[:n]]
    print(f"  top-{n} by USD volume: {top}", flush=True)
    return set(top)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=Path("data/reports/tf_universe_experiment.md"))
    args = ap.parse_args()

    env = load_unit_env()
    cfg = build_config(env)
    print("cfg: trail=%.3f TP=%.2f%% SL=%.1f%% ML>=%.2f conf>=%.2f" % (
        cfg.trail_ratio, cfg.take_profit_pct * 100, cfg.stop_loss_pct * 100,
        cfg.ml_min_prob_up, cfg.min_confidence), flush=True)

    # 1h full universe once; 4h derived
    s1h = build_series(env, None, "1h")
    top12 = top_universe(s1h, 12)
    s4h = build_series(env, None, "4h")
    print(f"series: 1h={len(s1h)} 4h={len(s4h)}", flush=True)

    # test window info (same calendar window across timeframes)
    for rule, s in (("1h", s1h), ("4h", s4h)):
        t0 = min(int(si["times"][int(len(si["times"]) * 0.70)]) for si in s.values())
        t1 = max(int(si["times"][-1]) for si in s.values())
        d0 = datetime.fromtimestamp(t0 / 1000, tz=UTC).strftime("%Y-%m-%d")
        d1 = datetime.fromtimestamp(t1 / 1000, tz=UTC).strftime("%Y-%m-%d")
        print(f"  {rule}: OOS window {d0} .. {d1}", flush=True)

    variants = [
        ("1h, все 33, RL вкл (как прод)", "1h", None, True, None),
        ("4h, все 33, RL вкл", "4h", None, True, None),
        ("1h, все 33, RL выкл", "1h", None, False, None),
        ("4h, все 33, RL выкл", "4h", None, False, None),
        ("1h, топ-12 ликвидности, RL выкл", "1h", top12, False, None),
        ("4h, топ-12 ликвидности, RL выкл", "4h", top12, False, None),
        ("4h, все 33, RL выкл, TP3%/SL1.5%", "4h", None, False,
         {"take_profit_pct": 0.03, "stop_loss_pct": -0.015}),
    ]

    results = {}
    for name, rule, universe, rl_on, override in variants:
        print(f"=== {name} ===", flush=True)
        s = s1h if rule == "1h" else s4h
        sub = {k: v for k, v in s.items() if universe is None or v["symbol"] in universe}
        probs = train_and_predict(sub)
        for key in sub:
            sub[key]["probs"] = probs[key]
        vcfg = cfg
        if override:
            from dataclasses import replace
            vcfg = replace(cfg, **override)
        res = run_backtest(sub, vcfg, probs, int(min(si["times"][int(len(si["times"]) * 0.70)]
                                                    for si in sub.values())),
                           rl_block=rl_on)
        m = summarize(res, vcfg)
        results[name] = m
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        print(f"  -> n={m['n']} wr={m['wr']:.1f}% pf={pf} pnl={m['pnl']:+.2f}$ "
              f"total={m['total_pnl']:+.2f}$", flush=True)

    # BTC bh over the same OOS window
    btc_key = next(k for k, s in s1h.items() if s["symbol"] == "BTC")
    sbtc = s1h[btc_key]
    i0 = int(len(sbtc["closes"]) * 0.70)
    bh = (float(sbtc["closes"][-1]) / float(sbtc["closes"][i0]) - 1.0) * 100.0
    print(f"BTC buy&hold (OOS): {bh:+.2f}%", flush=True)

    md = ["# Эксперимент: таймфрейм (1h/4h) × универсум × RL-вето (честный OOS)", "",
          "Методика: свежая CatBoost v2 per timeframe (train 70%, gap 48 баров), тест = последние "
          "~3.5 мес (календарно одинаково для 1h/4h). Движок 1:1 (текущий unit config: "
          f"trail={cfg.trail_ratio}, TP {cfg.take_profit_pct:.0%}, SL {cfg.stop_loss_pct:.0%}, "
          f"ML≥{cfg.ml_min_prob_up}, conf≥{cfg.min_confidence}, kill 0.25%). "
          "Топ-12 — по USD-объёму (volume×close) за 30 дней, выбор до прогона.",
          "",
          f"**BTC buy&hold за OOS-окно: {bh:+.2f}%**",
          "",
          "| Вариант | Сделок | Winrate | PF | PnL закрытых $ | Итог $ |",
          "|---|---:|---:|---:|---:|---:|"]
    for name, m in results.items():
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        md.append(f"| {name} | {m['n']} | {m['wr']:.1f}% | {pf} | {m['pnl']:+.2f} | "
                  f"{m['total_pnl']:+.2f} |")
    md += ["", "**Вывод:** если ни один вариант не дал PF>1.2 с n≥20 — edge не обнаружен "
              "и на 4h, и на топ-универсуме; решение о дальнейшем направлении за владельцем."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
