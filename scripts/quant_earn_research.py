#!/usr/bin/env python3
"""Second-wave research: find an algorithm that EARNS net of funding.

FIXED backtest engine vs v1:
  - COMPOUNDING: equity multiplies by (1 + pos*ret) each bar instead of
    summing arithmetic returns (summing overstates PnL on volatile assets);
  - TIMING: signal at close of bar t is applied to bar t+1 (correct
    next-bar semantics; v1 lagged one extra bar).

Strategies (daily bars unless noted), costs 0.25%/side + funding:
  - MA long/short (50/200, 60/240), funding base (short receives 0.03%/day)
    and stress (short pays 0.03%/day)
  - Donchian 20/55 long/short and long-only
  - MA long-only, MA double-filter long-only, RSI long-only
  - cross-sectional momentum long-only (weekly top-k)

Read-only. Report -> data/reports/earn_research.json / .md
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

COST_SIDE = 0.0015 + 0.0005 + 0.0005  # 0.25% per side
FUNDING_BASE = 0.0003  # short RECEIVES 0.03%/day (positive funding regime)
FUNDING_STRESS = -0.0003  # short PAYS 0.03%/day (conservative stress)


def load_symbols() -> dict[str, pd.DataFrame]:
    out = {}
    for path in sorted(glob.glob(str(QUANT_DIR / "*" / "binance" / "*_1h.csv"))):
        symbol = Path(path).stem.split("_")[0]
        if symbol in ("MATIC", "RNDR"):
            continue
        df = pd.read_csv(path).sort_values("timestamp_ms")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])
        if len(df) < 800:
            continue
        out[symbol] = df.reset_index(drop=True)
    return out


def resample(df: pd.DataFrame, hours: int = 24) -> pd.DataFrame:
    if hours == 1:
        return df.reset_index(drop=True)
    df = df.copy()
    df["bucket"] = df["timestamp_ms"] // (hours * 3_600_000)
    agg = df.groupby("bucket").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
        timestamp_ms=("timestamp_ms", "last"),
    ).reset_index(drop=True)
    return agg


def run_with_funding(df: pd.DataFrame, positions: np.ndarray, test_start: float,
                     funding_short_per_day: float, test_end: float | None = None) -> dict | None:
    """Compounded equity; signal at bar t applied to bar t+1 (no lookahead)."""
    closes = df["close"].values
    times = df["timestamp_ms"].values
    mask = times >= test_start
    if test_end is not None:
        mask = mask & (times < test_end)
    if mask.sum() < 50:
        return None
    pos = 0
    equity = 1.0
    trades = 0
    short_days = 0.0
    for i in range(len(df)):
        if not mask[i]:
            pos = int(positions[i]) if i < len(positions) else 0
            continue
        if i == 0:
            continue
        dt_h = (times[i] - times[i - 1]) / 3_600_000.0
        r = closes[i] / closes[i - 1] - 1.0 if closes[i - 1] > 0 else 0.0
        if pos != 0:
            equity *= (1.0 + pos * r)
            if pos < 0:
                short_days += dt_h / 24.0
        # adopt the signal decided at the close of the CURRENT bar (i):
        # it applies to the return of bar i+1 (true next-bar semantics).
        new_pos = int(positions[i]) if i < len(positions) else 0
        if new_pos != pos:
            equity *= (1.0 - COST_SIDE * (abs(new_pos) + abs(pos)))
            trades += 1
        pos = new_pos
    funding = short_days * funding_short_per_day
    net = equity * (1.0 + funding) - 1.0
    return {
        "gross_pct": round((equity - 1.0) * 100.0, 2),
        "funding_pct": round(funding * 100.0, 2),
        "net_pct": round(net * 100.0, 2),
        "trades": trades,
        "short_days": round(short_days, 1),
    }


def sig_ma(df, fast, slow, long_only=False):
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    pos = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if math.isnan(f[i]) or math.isnan(s[i]):
            pos[i] = 0
        elif f[i] > s[i]:
            pos[i] = 1
        elif long_only:
            pos[i] = 0
        else:
            pos[i] = -1
    return pos


def sig_donchian(df, entry_n=20, exit_n=55, long_only=False):
    hi = df["high"].rolling(entry_n).max().shift(1)
    lo = df["low"].rolling(entry_n).min().shift(1)
    hx = df["high"].rolling(exit_n).max().shift(1)
    lx = df["low"].rolling(exit_n).min().shift(1)
    pos = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if math.isnan(hi[i]):
            pos[i] = 0
            continue
        c = float(df["close"].iloc[i])
        if pos[i - 1] == 1:
            pos[i] = 0 if c < lx[i] else 1
        elif pos[i - 1] == -1:
            pos[i] = 0 if c > hx[i] else -1
        elif c > hi[i]:
            pos[i] = 1
        elif c < lo[i] and not long_only:
            pos[i] = -1
        else:
            pos[i] = 0
    return pos


def sig_rsi_longonly(df, lo=30):
    chg = df["close"].pct_change()
    up = chg.clip(lower=0).rolling(14).mean()
    down = (-chg.clip(upper=0)).rolling(14).mean()
    rsi = 100.0 - 100.0 / (1.0 + up / down.replace(0, 1e-9))
    pos = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if math.isnan(rsi[i]):
            pos[i] = 0
        elif rsi[i] < lo:
            pos[i] = 1
        else:
            pos[i] = 0
    return pos


def sig_ma_double_filter(df, fast=50, slow=200):
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    pos = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if math.isnan(f[i]) or math.isnan(s[i]):
            pos[i] = 0
        elif f[i] > s[i] and float(df["close"].iloc[i]) > s[i]:
            pos[i] = 1
        else:
            pos[i] = 0
    return pos


def cross_sectional_longonly(symbols: dict, test_start: float, k: int = 3,
                             period_days: int = 7) -> dict:
    daily = {s: resample(df, 24) for s, df in symbols.items()}
    all_ts = sorted({int(t) for d in daily.values() for t in d["timestamp_ms"].values})
    close_map = {s: dict(zip(d["timestamp_ms"].values, d["close"].values)) for s, d in daily.items()}
    ret_map = {}
    for s, d in daily.items():
        c = d["close"].values
        r = np.full(len(c), np.nan)
        r[period_days:] = c[period_days:] / c[:-period_days] - 1.0
        ret_map[s] = dict(zip(d["timestamp_ms"].values, r))
    equity = 1.0
    picks: list[str] = []
    bars = 0
    for t in all_ts:
        if t < test_start:
            continue
        if picks and bars > 0:
            day_ret = 0.0
            cnt = 0
            for s in picks:
                cp = close_map[s].get(t - 24 * 3_600_000)
                cn = close_map[s].get(t)
                if cp and cn:
                    day_ret += cn / cp - 1.0
                    cnt += 1
            if cnt:
                equity *= (1.0 + day_ret / cnt)
        bars += 1
        if bars % period_days != 0:
            continue
        scored = [(s, ret_map[s].get(t)) for s in ret_map
                  if ret_map[s].get(t) is not None and not math.isnan(ret_map[s].get(t))]
        scored.sort(key=lambda x: -x[1])
        new_picks = [s for s, _ in scored[:k]]
        turnover = 2 * k / max(1, len(scored))
        equity *= (1.0 - COST_SIDE * turnover)
        picks = new_picks
    return {"n": 0, "net_pct": round((equity - 1.0) * 100.0, 2), "trades": 0}


def main() -> int:
    symbols = load_symbols()
    print(f"loaded {len(symbols)} symbols (extended ~14-month history)")

    lens = sorted(len(df) for df in symbols.values())
    med_len = lens[len(lens) // 2]
    ts_30 = 0.0
    ts_50 = 0.0
    for df in symbols.values():
        if len(df) == med_len:
            ts_30 = float(df["timestamp_ms"].iloc[int(med_len * 0.70)])
            ts_50 = float(df["timestamp_ms"].iloc[int(med_len * 0.50)])
            break
    print(f"OOS30 starts {int(ts_30)}, OOS50 starts {int(ts_50)}")

    strategies = {
        "MA_LS_50_200": lambda d: sig_ma(d, 50, 200),
        "MA_LS_60_240": lambda d: sig_ma(d, 60, 240),
        "Donchian_20_55_LS": lambda d: sig_donchian(d, 20, 55),
        "Donchian_20_55_LONG": lambda d: sig_donchian(d, 20, 55, long_only=True),
        "MA_LS_50_200_LONG": lambda d: sig_ma(d, 50, 200, long_only=True),
        "MA_double_filter_LONG": lambda d: sig_ma_double_filter(d, 50, 200),
        "RSI_daily_LONG": lambda d: sig_rsi_longonly(d, 30),
    }

    report: dict = {}
    print(f"\n{'Strategy':<26} {'Split':<6} {'NetBase%':>9} {'NetStress%':>10} {'Trades':>7}")
    print("-" * 66)
    for name, fn in strategies.items():
        for split, ts in [("70/30", ts_30), ("50/50", ts_50)]:
            nets_base = []
            nets_stress = []
            agg_trades = 0
            n = 0
            for symbol, df in symbols.items():
                g = resample(df, 24)
                pos = fn(g)
                rb = run_with_funding(g, pos, ts, FUNDING_BASE)
                rs = run_with_funding(g, pos, ts, FUNDING_STRESS)
                if rb is None:
                    continue
                nets_base.append(rb["net_pct"])
                nets_stress.append(rs["net_pct"])
                agg_trades += rb["trades"]
                n += 1
            # equal-weight portfolio: average of per-symbol equity curves
            net_base = sum(nets_base) / n
            net_stress = sum(nets_stress) / n
            key = f"{name}__{split}"
            report[key] = {
                "net_base_pct": round(net_base, 2),
                "net_stress_pct": round(net_stress, 2),
                "trades": agg_trades,
                "n": n,
            }
            print(f"{name:<26} {split:<6} {net_base:>+8.2f}% {net_stress:>+9.2f}% {agg_trades:>7}")

    # cross-sectional long-only momentum
    for k, p in [(3, 7), (5, 7)]:
        r = cross_sectional_longonly(symbols, ts_30, k=k, period_days=p)
        report[f"XS_long_mom_top{k}_p{p}__70/30"] = r
        print(f"XS_long_mom_top{k}_p{p}     70/30  {r['net_pct']:>+7.2f}%  (net)")

    out = REPO_ROOT / "data" / "reports" / "earn_research.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("\nreport ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
