#!/usr/bin/env python3
"""Basket/DCA variants backtest (Edge Lab 2026-08-17, passive wing).

The scoreboard showed the equal-weight top-10 basket as the only robust
winner. This harness asks the next practical question on 12 months of 1h
history (2025-08-18 -> 2026-08-18): which passive variant wins?

Variants (a-priori, fixed BEFORE looking at results):
  V0: monthly rebalance (baseline = live basket paper)
  V1: weekly rebalance
  V2: quarterly rebalance
  V3: monthly + trend filter (fully invested only when BTC daily > SMA200)
  V4: monthly + vol targeting (weights ∝ 1/σ_30d, normalized)
  V5: weekly DCA $25 (≈$100/mo, baseline DCA)
  V6: weekly DCA + trend filter (cash accumulates, deployed on filter pass)

Costs: 0.1% per traded leg. TON: binance series ends 2026-06-30 (delisted),
stitched with kraken from 2026-07-16 (gap frozen at last price — conservative).

Read-only; writes data/reports/basket_variants_report.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
QUANT_DIR = REPO_ROOT / "data" / "quant"

TOP10 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "TRX", "TON", "ADA", "LINK"]
FEE = 0.001
START_CAPITAL = 1000.0


# ---------------------------------------------------------------- data ------
def load_1h(symbol: str) -> pd.Series | None:
    csv_paths = sorted(QUANT_DIR.glob(f"{symbol}/binance/{symbol}_1h.csv"))
    if not csv_paths:
        return None
    df = pd.read_csv(csv_paths[0]).sort_values("timestamp_ms")
    s = pd.Series(df["close"].values,
                  index=pd.to_datetime(df["timestamp_ms"], unit="ms"))
    return s[~s.index.duplicated(keep="last")]


def stitch_ton(binance: pd.Series, kraken: pd.Series) -> pd.Series:
    """Normalize kraken onto binance at the overlap and concatenate (pure)."""

    if binance is None:
        return kraken
    if kraken is None:
        return binance
    overlap_start = kraken.index.min()
    if overlap_start > binance.index.max():
        # нет перекрытия: консервативно оставляем binance, хвост — заморозка
        return binance
    b_overlap = binance.loc[:overlap_start]
    if b_overlap.empty:
        return binance
    ratio = kraken.loc[overlap_start] / b_overlap.iloc[-1]
    kraken_norm = kraken / ratio
    return pd.concat([b_overlap.iloc[:-1], kraken_norm])


def daily_frame(symbols: list[str]) -> pd.DataFrame:
    """UTC-daily closes (last 1h bar of the day), ffill for gaps."""

    series = {}
    for sym in symbols:
        s = load_1h(sym)
        if sym == "TON":
            k_paths = sorted(QUANT_DIR.glob("TON/kraken/TON_1h.csv"))
            k = None
            if k_paths:
                kdf = pd.read_csv(k_paths[0]).sort_values("timestamp_ms")
                k = pd.Series(kdf["close"].values,
                              index=pd.to_datetime(kdf["timestamp_ms"], unit="ms"))
            s = stitch_ton(s, k)
        if s is not None:
            d = s.resample("1D").last().dropna()
            series[sym] = d
    frame = pd.DataFrame(series).sort_index()
    frame = frame.ffill()
    return frame


# ---------------------------------------------------------------- helpers ----
def trend_filter_mask(btc: pd.Series, window: int = 200) -> pd.Series:
    """True when BTC daily close is above its SMA(window)."""

    sma = btc.rolling(window).mean()
    return btc > sma


def vol_weights(prices: pd.DataFrame, as_of: pd.Timestamp,
                window: int = 30) -> pd.Series:
    """Weights ∝ 1/rolling std of daily returns, normalized to sum 1 (pure)."""

    rets = prices.pct_change().iloc[-window:]
    vol = rets.std()
    vol = vol.replace(0, np.nan)
    inv = 1.0 / vol
    inv = inv.fillna(inv.mean())
    return inv / inv.sum()


def metrics(equity: pd.Series) -> dict:
    """Total return %, max drawdown %, daily Sharpe, final equity (pure)."""

    if len(equity) < 2:
        return {"total_pct": 0.0, "max_dd_pct": 0.0, "sharpe": 0.0,
                "final_equity": float(equity.iloc[-1] if len(equity) else START_CAPITAL)}
    rets = equity.pct_change().dropna()
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0) * 100
    dd = (equity / equity.cummax() - 1.0).min() * 100
    sharpe = float(rets.mean() / rets.std() * np.sqrt(365)) if rets.std() > 0 else 0.0
    return {"total_pct": round(total, 2), "max_dd_pct": round(float(dd), 2),
            "sharpe": round(sharpe, 2), "final_equity": round(float(equity.iloc[-1]), 2)}


def simulate_rebalance(prices: pd.DataFrame, rule: str, *,
                       filter_mask: pd.Series | None = None,
                       weights_fn=None, fee: float = FEE,
                       capital: float = START_CAPITAL) -> tuple[pd.Series, int]:
    """Rebalanced basket simulation; rule in {weekly, monthly, quarterly}."""

    freq = {"weekly": "W", "monthly": "MS", "quarterly": "QS"}[rule]
    dates = pd.date_range(prices.index.min(), prices.index.max(), freq=freq)
    holdings = pd.Series(0.0, index=prices.columns)
    cash = capital
    equity = []
    n_trades = 0
    invested = filter_mask is None or bool(filter_mask.loc[prices.index.min()])
    last_date = prices.index[0]
    for d in prices.index:
        # ребаланс в начале недели/месяца/квартала (или первый день окна)
        if d in dates or d == prices.index[0]:
            allowed = bool(filter_mask.loc[d]) if filter_mask is not None else True
            if allowed:
                if weights_fn is not None:
                    w = weights_fn(prices.loc[:d], d)
                else:
                    w = pd.Series(1.0 / len(prices.columns), index=prices.columns)
                value = cash + float((holdings * prices.loc[d]).sum())
                target = (value * w / prices.loc[d]).fillna(0.0)
                diff = target - holdings
                traded = float(diff.abs().dot(prices.loc[d]))
                flow = float(diff.dot(prices.loc[d]))  # покупки тратят кэш, продажи возвращают
                cash -= flow
                cash -= traded * fee
                n_trades += int((diff.abs() > 1e-12).sum())
                holdings = target
                invested = True
            else:
                # тренд-фильтр: всё в кэш (комиссия за ликвидацию)
                held_value = float((holdings * prices.loc[d]).sum())
                value = cash + held_value
                cash = value - held_value * fee
                holdings = pd.Series(0.0, index=prices.columns)
                invested = False
        equity.append(cash + float((holdings * prices.loc[d]).sum()))
        last_date = d
    eq = pd.Series(equity, index=prices.index)
    return eq, n_trades


def simulate_dca(prices: pd.DataFrame, weekly: float, *,
                 filter_mask: pd.Series | None = None,
                 fee: float = FEE,
                 capital: float = START_CAPITAL) -> tuple[pd.Series, int]:
    """Weekly DCA: buy `weekly` equally across the basket (or accumulate cash
    under the trend filter and deploy everything on the first passing week)."""

    dates = pd.date_range(prices.index.min(), prices.index.max(), freq="W")
    holdings = pd.Series(0.0, index=prices.columns)
    cash = capital
    equity = []
    n_buys = 0
    for d in prices.index:
        if d in dates and d != prices.index[0]:
            allowed = bool(filter_mask.loc[d]) if filter_mask is not None else True
            if allowed:
                amount = min(weekly, cash)
                px = prices.loc[d]
                qty = (amount / len(prices.columns)) * (1 - fee) / px
                holdings += qty.fillna(0.0)
                cash -= amount
                n_buys += 1
        equity.append(cash + float((holdings * prices.loc[d]).sum()))
    eq = pd.Series(equity, index=prices.index)
    return eq, n_buys


# -------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "data" / "reports" / "basket_variants_report.md")
    ap.add_argument("--start", default="2025-08-18")
    ap.add_argument("--end", default="2026-08-18")
    args = ap.parse_args()

    prices = daily_frame(TOP10)
    prices = prices.loc[args.start:args.end].ffill()
    # символы без покрытия всего окна (после ff) — допустимы; TON заморожен
    print(f"окно: {prices.index.min().date()} -> {prices.index.max().date()}, "
          f"символов: {prices.shape[1]}", flush=True)

    btc = prices["BTC"]
    filt = trend_filter_mask(btc, 200)

    variants = [
        ("V0 monthly (baseline)", lambda: simulate_rebalance(prices, "monthly")),
        ("V1 weekly", lambda: simulate_rebalance(prices, "weekly")),
        ("V2 quarterly", lambda: simulate_rebalance(prices, "quarterly")),
        ("V3 monthly + trend BTC>SMA200", lambda: simulate_rebalance(prices, "monthly", filter_mask=filt)),
        ("V4 monthly + vol targeting", lambda: simulate_rebalance(prices, "monthly", weights_fn=vol_weights)),
        ("V5 DCA weekly $25", lambda: simulate_dca(prices, 25.0)),
        ("V6 DCA weekly + trend filter", lambda: simulate_dca(prices, 25.0, filter_mask=filt)),
    ]

    results = []
    for name, fn in variants:
        eq, trades = fn()
        m = metrics(eq)
        m["name"] = name
        m["n_trades"] = trades
        results.append(m)
        print(f"{name}: {m['total_pct']:+.2f}% DD {m['max_dd_pct']:.1f}% "
              f"Sharpe {m['sharpe']:.2f} trades={trades} final=${m['final_equity']}", flush=True)

    btc_ret = (prices["BTC"].iloc[-1] / prices["BTC"].iloc[0] - 1) * 100
    lines = [
        "# Вариации пассивной корзины/DCA (Edge Lab 2026-08-17)",
        "",
        f"Окно: {args.start} → {args.end} (12 мес, UTC-daily из 1h) | издержки 0.1%/лег | старт $1000",
        f"Символы: {', '.join(prices.columns)} (TON: binance→kraken стык, дыра 01-15.07 заморожена)",
        "",
        f"BTC buy&hold за окно: **{btc_ret:+.2f}%**",
        "",
        "| Вариант | PnL % | MaxDD % | Sharpe | Сделок | Итог $ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        lines.append(f"| {r['name']} | {r['total_pct']:+.2f} | {r['max_dd_pct']:.1f} "
                     f"| {r['sharpe']:.2f} | {r['n_trades']} | {r['final_equity']:.2f} |")
    lines += ["", "Вывод: см. docs/BASKET_VARIANTS_2026-08-17_RU.md."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
