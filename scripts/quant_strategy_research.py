#!/usr/bin/env python3
"""Systematic strategy research: find a strategy with positive OOS PnL.

Tests families of strategies over the same honest OOS window (last 30% of
history) with costs (0.15% fee + 0.05% half-spread + 0.05% slippage per side):
  A. long-only baselines (Buy&Hold, cash)
  B. trend-following long/short (daily & 4h SMA crosses)
  C. RSI mean-reversion long/short (daily & 4h)
  D. ML direction long/short (model retrained on the train window only!)
  E. inverted-ML (contrarian)
  F. regime filter (quant_regime_v3): trend_up -> long, trend_down -> short
  G. cross-sectional momentum / mean-reversion (weekly top/bottom-3)
  H. BTC-regime gate (trade BTC only when BTC daily trend is up)

Signals are computed at bar close t and the position is applied to bar t+1
(no lookahead). Equal-weight portfolio across symbols; position 100% of the
symbol slice. Read-only; report -> data/reports/strategy_research.json/.md.

Usage:
    python scripts/quant_strategy_research.py
"""

from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUANT_DIR = REPO_ROOT / "data" / "quant"

FEE = 0.0015
HALF_SPREAD = 0.0005
SLIPPAGE = 0.0005
COST_SIDE = FEE + HALF_SPREAD + SLIPPAGE  # 0.25% per side

TRAIN_FRAC = 0.70
GAP_BARS_1H = 48

FEATURES = [
    "ret1", "ret3", "ret6", "ret12", "ret24",
    "rsi", "bb_pos", "macd_norm", "ema_gap",
    "vol_ratio", "vol_z", "bar_range_pct", "hl_pos",
]


def _compute_features(df: pd.DataFrame) -> pd.DataFrame:
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


def resample(df: pd.DataFrame, hours: int) -> pd.DataFrame:
    """Aggregate 1h bars to `hours` bars (close-to-close OHLCV)."""
    if hours == 1:
        return df.reset_index(drop=True)
    df = df.copy()
    df["bucket"] = df["timestamp_ms"] // (hours * 3_600_000)
    agg = df.groupby("bucket").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        timestamp_ms=("timestamp_ms", "last"),
    ).reset_index(drop=True)
    return agg


def load_symbols() -> dict[str, pd.DataFrame]:
    out = {}
    for path in sorted(glob.glob(str(QUANT_DIR / "*" / "binance" / "*_1h.csv"))):
        symbol = Path(path).stem.split("_")[0]
        if symbol in ("MATIC", "RNDR"):
            continue
        df = pd.read_csv(path).sort_values("timestamp_ms")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])
        if len(df) < 600:
            continue
        out[symbol] = df.reset_index(drop=True)
    return out


def run_strategy(symbols: dict[str, pd.DataFrame], signal_fn, *, hours: int = 1,
                 test_start: float) -> dict:
    """Equal-weight portfolio; position = {1: long, 0: cash, -1: short} on next bar.

    signal_fn(history_df) -> position for the NEXT bar (no lookahead: the
    signal uses only bars up to and including the current one).
    """
    total_ret = 0.0
    n_traded = 0
    per_symbol = {}
    for symbol, df1h in symbols.items():
        df = resample(df1h, hours)
        closes = df["close"].values
        times = df["timestamp_ms"].values
        mask = times >= test_start
        if mask.sum() < 100:
            continue
        # signals on the whole series
        positions = signal_fn(df)
        if positions is None or len(positions) != len(df):
            continue
        pos = 0
        ret_sum = 0.0
        trades = 0
        for i in range(len(df)):
            if not mask[i]:
                pos = positions[i]  # keep updating position pre-test too
                continue
            if i == 0:
                continue
            # return of bar i applied to position held from previous close
            r = closes[i] / closes[i - 1] - 1.0 if closes[i - 1] > 0 else 0.0
            if pos != 0:
                ret_sum += pos * r
            new_pos = positions[i - 1]  # position decided at bar i-1 close
            if new_pos != pos:
                # transaction cost on the side being closed + opened
                ret_sum -= COST_SIDE * (abs(new_pos) + abs(pos))
                trades += 1
            pos = new_pos
        per_symbol[symbol] = round(ret_sum * 100.0, 3)
        total_ret += ret_sum
        n_traded += 1
    if n_traded == 0:
        return {"n": 0, "pnl_pct": 0.0, "per_symbol": {}, "avg_trades": 0}
    return {
        "n": n_traded,
        "pnl_pct": round(total_ret / n_traded * 100.0, 3),
        "per_symbol": per_symbol,
        "avg_trades": 0,
    }


# ------------------------------------------------------------- signals ----
def sig_bh(df):
    return np.ones(len(df), dtype=int)


def sig_cash(df):
    return np.zeros(len(df), dtype=int)


def sig_ma(df, fast, slow):
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    pos = np.zeros(len(df), dtype=int)
    up = f > s
    for i in range(len(df)):
        if math.isnan(f[i]) or math.isnan(s[i]):
            pos[i] = 0
        elif up[i]:
            pos[i] = 1
        else:
            pos[i] = -1
    return pos


def sig_rsi(df, lo=30, hi=70):
    rsi = df["rsi"].values if "rsi" in df else None
    pos = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if rsi is None or math.isnan(rsi[i]):
            pos[i] = 0
        elif rsi[i] < lo:
            pos[i] = 1
        elif rsi[i] > hi:
            pos[i] = -1
        else:
            pos[i] = 0
    return pos


def sig_ml(df, prob_col, buy_thr, sell_thr, invert=False):
    p = df[prob_col].values
    pos = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if math.isnan(p[i]):
            pos[i] = 0
        elif not invert and p[i] >= buy_thr:
            pos[i] = 1
        elif not invert and p[i] <= sell_thr:
            pos[i] = -1
        elif invert and p[i] <= sell_thr:
            pos[i] = 1
        elif invert and p[i] >= buy_thr:
            pos[i] = -1
        else:
            pos[i] = 0
    return pos


def sig_regime(df):
    sys.path.insert(0, str(REPO_ROOT))
    from aios_core.quant_regime_v3 import compute_regime_features

    rows = [
        {"timestamp": float(r.timestamp_ms), "open": float(r.open), "high": float(r.high),
         "low": float(r.low), "close": float(r.close), "volume": float(r.volume)}
        for r in df.itertuples()
    ]
    feats = compute_regime_features(rows)
    pos = np.zeros(len(df), dtype=int)
    for i, f in enumerate(feats):
        if f["regime"] == "trend_up":
            pos[i] = 1
        elif f["regime"] == "trend_down":
            pos[i] = -1
        else:
            pos[i] = 0
    return pos


def sig_btc_gate(df, btc_daily_up: np.ndarray, btc_times: np.ndarray):
    """Long BTC only when BTC daily trend is up; else cash."""
    pos = np.zeros(len(df), dtype=int)
    ts = df["timestamp_ms"].values
    for i in range(len(df)):
        idx = np.searchsorted(btc_times, ts[i], side="right") - 1
        if idx >= 0 and btc_daily_up[idx]:
            pos[i] = 1
    return pos


def main() -> int:
    symbols = load_symbols()
    print(f"loaded {len(symbols)} symbols")

    # Global test start = 70% of the longest series (common OOS window).
    last_ts = max(int(df["timestamp_ms"].iloc[-1]) for df in symbols.values())
    # Use the median series length to define the train/test split fairly.
    lens = sorted(len(df) for df in symbols.values())
    med_len = lens[len(lens) // 2]
    # test start: 70% through the median-length series
    test_start = 0.0
    for df in symbols.values():
        if len(df) == med_len:
            test_start = float(df["timestamp_ms"].iloc[int(med_len * TRAIN_FRAC)])
            break
    print("OOS window starts at ts", int(test_start))

    # ---- ML: retrain on the train window only (honest) ----
    from catboost import CatBoostClassifier

    frames = []
    for symbol, df in symbols.items():
        g = _compute_features(df)
        clean = g.dropna(subset=FEATURES + ["target"] if "target" in g else FEATURES)
        g["target"] = (g["close"].shift(-1) > g["close"]).astype(int)
        clean = g.dropna(subset=FEATURES + ["target"]).reset_index(drop=True)
        cut = int(len(clean) * TRAIN_FRAC)
        frames.append((symbol, clean.iloc[: cut - GAP_BARS_1H], clean.iloc[cut:]))
    train_parts = [tr for _, tr, _ in frames if len(tr) > 100]
    df_train = pd.concat(train_parts, ignore_index=True)
    model = CatBoostClassifier(
        iterations=400, depth=5, learning_rate=0.03, l2_leaf_reg=5.0,
        loss_function="Logloss", eval_metric="AUC", random_seed=42,
        verbose=0, thread_count=-1,
    )
    model.fit(df_train[FEATURES].values.astype(np.float64), df_train["target"].values.astype(int))
    print("ML retrained on train window only")

    # Precompute ML probs per symbol (on features aligned to 1h bars).
    ml_probs: dict[str, np.ndarray] = {}
    for symbol, df in symbols.items():
        g = _compute_features(df)
        X = g[FEATURES].values.astype(np.float64)
        probs = model.predict_proba(X)[:, 1]
        ml_probs[symbol] = probs

    # Precompute daily BTC trend for the BTC-gate strategy.
    btc = resample(symbols["BTC"], 24)
    btc_f = btc["close"].rolling(50).mean()
    btc_s = btc["close"].rolling(200).mean()
    btc_up = (btc_f > btc_s).values.astype(int)
    btc_times = btc["timestamp_ms"].values

    # ---- assemble strategies ----
    strategies: list[tuple[str, dict]] = []
    for hours, name, fn in [
        (1, "BH", sig_bh),
        (1, "Cash", sig_cash),
        (24, "MA_daily_LS", lambda d: sig_ma(d, 50, 200)),
        (4, "MA_4h_LS", lambda d: sig_ma(d, 20, 50)),
        (24, "RSI_daily_MR", lambda d: sig_rsi(d)),
        (4, "RSI_4h_MR", lambda d: sig_rsi(d)),
    ]:
        res = run_strategy(symbols, fn, hours=hours, test_start=test_start)
        strategies.append((f"{name} [{hours}h]", res))

    def ml_sig(symbol, buy, sell, invert=False):
        def fn(df):
            return sig_ml(df, "ml_prob", buy, sell, invert)
        return fn

    # ML strategies per symbol need per-symbol probs -> custom runner.
    for name, buy, sell, invert in [
        ("ML_LS_055_045", 0.55, 0.45, False),
        ("ML_LS_050_045", 0.50, 0.45, False),
        ("ML_INV_045_055", 0.55, 0.45, True),
        ("ML_LS_060_040", 0.60, 0.40, False),
    ]:
        total_ret = 0.0
        n = 0
        per = {}
        for symbol, df in symbols.items():
            g = _compute_features(df)
            g["ml_prob"] = ml_probs[symbol]
            res = run_strategy({symbol: g}, lambda d, s=symbol: sig_ml(d, "ml_prob", buy, sell, invert),
                               hours=1, test_start=test_start)
            if res["n"]:
                per[symbol] = res["pnl_pct"]
                total_ret += res["pnl_pct"]
                n += 1
        strategies.append((f"{name} [1h]", {"n": n, "pnl_pct": round(total_ret / n, 3) if n else 0.0,
                                            "per_symbol": per, "avg_trades": 0}))

    # Regime strategy (1h) — single portfolio run is fine but slow; do per-symbol.
    total_ret = 0.0
    n = 0
    per = {}
    for symbol, df in symbols.items():
        res = run_strategy({symbol: df}, sig_regime, hours=1, test_start=test_start)
        if res["n"]:
            per[symbol] = res["pnl_pct"]
            total_ret += res["pnl_pct"]
            n += 1
    strategies.append(("Regime_LS [1h]", {"n": n, "pnl_pct": round(total_ret / n, 3) if n else 0.0,
                                           "per_symbol": per, "avg_trades": 0}))

    # BTC-gate (trade only BTC with daily trend filter)
    res = run_strategy({"BTC": symbols["BTC"]},
                       lambda d: sig_btc_gate(d, btc_up, btc_times),
                       hours=1, test_start=test_start)
    strategies.append(("BTC_daily_gate [1h]", res))

    # Cross-sectional momentum / mean-reversion (weekly rebalance, top/bottom-3)
    # Implemented directly on daily closes across symbols.
    def cross_sectional(top: bool, k: int = 3, period_days: int = 7):
        daily = {s: resample(df, 24) for s, df in symbols.items()}
        # common daily timeline
        all_ts = sorted({int(t) for d in daily.values() for t in d["timestamp_ms"].values})
        test_days = [t for t in all_ts if t >= test_start]
        # build close matrix
        close_map = {s: dict(zip(d["timestamp_ms"].values, d["close"].values)) for s, d in daily.items()}
        ret_map = {}
        for s, d in daily.items():
            c = d["close"].values
            r = np.full(len(c), np.nan)
            r[period_days:] = c[period_days:] / c[:-period_days] - 1.0
            ret_map[s] = dict(zip(d["timestamp_ms"].values, r))
        portfolio = 0.0
        invested = False
        picks: list[str] = []
        bars = 0
        for t in test_days:
            if invested and bars > 0:
                # hold return of current picks for this day
                day_ret = 0.0
                cnt = 0
                for s in picks:
                    c_prev = close_map[s].get(t - 24 * 3_600_000)
                    c_now = close_map[s].get(t)
                    if c_prev and c_now:
                        day_ret += c_now / c_prev - 1.0
                        cnt += 1
                if cnt:
                    portfolio += day_ret / cnt
            bars += 1
            if bars % period_days != 0:
                continue
            # rebalance day: rank by ret over period
            scored = []
            for s, rm in ret_map.items():
                r = rm.get(t)
                if r is not None and not math.isnan(r):
                    scored.append((s, r))
            scored.sort(key=lambda x: x[1], reverse=top)
            new_picks = [s for s, _ in scored[:k]]
            # costs on rebalance (turnover ~ 2*k / n)
            turnover = 2 * k / max(1, len(scored))
            portfolio -= COST_SIDE * turnover
            picks = new_picks
            invested = True
        return {"n": len(test_days), "pnl_pct": round(portfolio * 100.0, 3), "per_symbol": {}, "avg_trades": 0}

    strategies.append(("XS_momentum_top3 [1d]", cross_sectional(top=True)))
    strategies.append(("XS_meanrev_bot3 [1d]", cross_sectional(top=False)))

    # ---- report ----
    rows = sorted(strategies, key=lambda x: -x[1]["pnl_pct"])
    print("\n=== STRATEGY RESEARCH (OOS window) ===")
    print(f"{'Strategy':<24} {'PnL %':>9} {'Symbols':>8}")
    print("-" * 46)
    for name, res in rows:
        print(f"{name:<24} {res['pnl_pct']:>+8.2f}% {res['n']:>8}")

    report = {
        "test_start_ts": int(test_start),
        "note": (
            "OOS = last 30% of history; costs 0.25%/side; signals on close t, "
            "position applied to bar t+1; equal-weight symbols; ML retrained on "
            "train window only; cross-sectional rebalances weekly."
        ),
        "strategies": {name: res for name, res in rows},
    }
    out = REPO_ROOT / "data" / "reports" / "strategy_research.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("report ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
