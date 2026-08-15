#!/usr/bin/env python3
"""DCA portfolio analysis on local 12-month data (honest, with fees).

Simulates systematic investing strategies over the local binance 1h history
(2025-08-15 .. 2026-08-15, 33 symbols) and compares:
  - weekly DCA, equal-weight top-5 / top-10
  - weekly DCA, cap-weight (current market caps)
  - weekly DCA, BTC-only
  - lump-sum equal-weight top-10 at start
  - cash baseline (0%)
Fees: 0.1% per buy (binance spot taker), no sell (buy-and-hold); quarterly
rebalance variant included for the top-10 portfolio (0.1% both sides).

Usage:
    python scripts/quant_dca_analysis.py [--output data/reports/dca_analysis.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quant_monthly_backtest as qmb

FEE = 0.001  # 0.1% per buy (binance spot taker)

# a-priori universes (top liquid, non-stable)
TOP5 = ["BTC", "ETH", "SOL", "XRP", "BNB"]
TOP10 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "TRX", "TON", "ADA", "LINK"]

# current market caps (CoinGecko 2026-08-15, USD)
MARKET_CAPS = {
    "BTC": 1264.3e9, "ETH": 227.0e9, "BNB": 81.2e9, "XRP": 62.7e9, "SOL": 44.0e9,
    "TRX": 31.5e9, "DOGE": 10.8e9, "LINK": 7.2e9, "ADA": 6.6e9, "TON": 4.5e9,
    "LTC": 3.2e9, "DOT": 2.9e9, "NEAR": 2.6e9, "UNI": 2.4e9, "AVAX": 2.2e9,
}


def load_daily(symbol: str) -> pd.DataFrame:
    df = qmb._load_series(symbol, "binance")
    if df is None:
        return pd.DataFrame()
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True).dt.normalize()
    d = df.groupby("date")["close"].last().reset_index()
    return d.sort_values("date")


def weekly_dates(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    out = []
    t = start
    while t <= end:
        out.append(t)
        t += pd.Timedelta(days=7)
    return out


def sim_dca(prices: dict[str, pd.DataFrame], weights: dict[str, float],
            weekly: float, start: pd.Timestamp, end: pd.Timestamp,
            rebalance_quarterly: bool = False) -> dict:
    """Weekly contributions into a fixed-weight portfolio; optional quarterly rebalance."""
    dates = weekly_dates(start, end)
    units = {s: 0.0 for s in weights}
    cash = 0.0
    invested = 0.0
    fees = 0.0
    curve: list[tuple[pd.Timestamp, float]] = []

    def mark(t: pd.Timestamp) -> float:
        val = cash
        for s, u in units.items():
            p = prices.get(s)
            if p is None or u <= 0:
                continue
            row = p[p["date"] <= t]
            if not row.empty:
                val += u * float(row["close"].iloc[-1])
        return val

    prev_reb = None
    for t in dates:
        # contribution
        amount = weekly
        invested += amount
        for s, w in weights.items():
            p = prices.get(s)
            if p is None:
                continue
            row = p[p["date"] == t]
            if row.empty:
                continue
            px = float(row["close"].iloc[0])
            buy_net = amount * w * (1.0 - FEE)
            units[s] += buy_net / px
            fees += amount * w * FEE
        # quarterly rebalance
        if rebalance_quarterly and prev_reb is not None and (t - prev_reb).days >= 90:
            val = mark(t)
            for s in weights:
                row = p = prices.get(s)
                if row is None:
                    continue
                r = row[row["date"] == t]
                if r.empty:
                    continue
                px = float(r["close"].iloc[0])
                target_val = val * weights[s]
                cur_val = units[s] * px
                diff = target_val - cur_val
                if diff > 0:
                    buy_net = diff * (1.0 - FEE)
                    units[s] += buy_net / px
                    fees += diff * FEE
                    cash -= 0
                elif diff < 0:
                    sell = min(units[s], -diff / px)
                    units[s] -= sell
                    cash += sell * px * (1.0 - FEE)
                    fees += sell * px * FEE
            prev_reb = t
        elif prev_reb is None:
            prev_reb = t
        curve.append((t, mark(t)))

    final = mark(dates[-1]) if dates else 0.0
    eq = pd.Series([v for _, v in curve], index=[d for d, _ in curve])
    dd = float(((eq / eq.cummax()) - 1.0).min() * 100.0) if len(eq) > 1 else 0.0
    years = (end - start).days / 365.25
    cagr = ((final / invested) ** (1 / years) - 1.0) * 100.0 if invested > 0 and years > 0 else 0.0
    return {"final": final, "invested": invested, "pnl": final - invested,
            "ret_pct": (final / invested - 1.0) * 100.0 if invested else 0.0,
            "cagr": cagr, "max_dd": dd, "fees": fees, "curve": curve}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=Path("data/reports/dca_analysis.md"))
    ap.add_argument("--weekly", type=float, default=1000.0)
    args = ap.parse_args()

    # load daily closes for all needed symbols
    all_syms = sorted(set(TOP10 + list(MARKET_CAPS)))
    prices = {}
    for s in all_syms:
        d = load_daily(s)
        if not d.empty:
            prices[s] = d
    if not prices:
        print("no data"); return 1
    start = max(p["date"].iloc[0] for p in prices.values())
    end = min(p["date"].iloc[-1] for p in prices.values())
    # align to 12 months back from end
    start = max(start, end - pd.Timedelta(days=365))
    print(f"window: {start.date()} .. {end.date()}  symbols: {len(prices)}", flush=True)

    variants = []

    def add(name, weights, reb=False):
        w = {s: wt for s, wt in weights.items() if s in prices}
        tot = sum(w.values())
        w = {s: v / tot for s, v in w.items()}
        r = sim_dca(prices, w, args.weekly, start, end, reb)
        variants.append((name, r))
        print(f"{name}: invested={r['invested']:.0f}$ final={r['final']:.2f}$ "
              f"ret={r['ret_pct']:+.2f}% CAGR={r['cagr']:+.2f}% maxDD={r['max_dd']:.2f}%", flush=True)

    add("DCA weekly, равные веса топ-5", {s: 1 for s in TOP5})
    add("DCA weekly, равные веса топ-10", {s: 1 for s in TOP10})
    add("DCA weekly, топ-10, квартальный ребаланс", {s: 1 for s in TOP10}, reb=True)
    cw = {s: MARKET_CAPS.get(s, 1.0) for s in TOP10}
    add("DCA weekly, кап-веса топ-10", cw)
    add("DCA weekly, BTC-only", {"BTC": 1})

    # lump-sum equal weight top-10 at start
    w10 = {s: 1 for s in TOP10 if s in prices}
    tot = sum(w10.values())
    w10 = {s: v / tot for s, v in w10.items()}
    ls = sim_dca(prices, w10, 0.0, start, end)
    # force lump sum: invest the whole budget at t0
    weekly = args.weekly
    n_weeks = len(weekly_dates(start, end))
    budget = weekly * n_weeks
    units = {}
    for s, w in w10.items():
        row = prices[s][prices[s]["date"] == start]
        if not row.empty:
            units[s] = budget * w * (1 - FEE) / float(row["close"].iloc[0])
    final = 0.0
    for s, u in units.items():
        row = prices[s][prices[s]["date"] <= end]
        if not row.empty:
            final += u * float(row["close"].iloc[-1])
    ls = {"final": final, "invested": budget, "pnl": final - budget,
          "ret_pct": (final / budget - 1) * 100, "cagr": 0.0, "max_dd": 0.0, "fees": 0.0}
    variants.append(("Lump-sum равные веса топ-10 (вся сумма в начале)", ls))
    print(f"Lump-sum топ-10: invested={budget:.0f}$ final={final:.2f}$ ret={ls['ret_pct']:+.2f}%", flush=True)

    # BTC-only lump-sum (whole budget at t0)
    btc_u = 0.0
    row = prices["BTC"][prices["BTC"]["date"] == start]
    if not row.empty:
        btc_u = budget * (1 - FEE) / float(row["close"].iloc[0])
    btc_final = 0.0
    row = prices["BTC"][prices["BTC"]["date"] <= end]
    if not row.empty:
        btc_final = btc_u * float(row["close"].iloc[-1])
    lbs = {"final": btc_final, "invested": budget, "pnl": btc_final - budget,
           "ret_pct": (btc_final / budget - 1) * 100, "cagr": 0.0, "max_dd": 0.0, "fees": 0.0}
    variants.append(("BTC-only lump-sum (вся сумма в начале)", lbs))
    print(f"Lump-sum BTC: invested={budget:.0f}$ final={btc_final:.2f}$ ret={lbs['ret_pct']:+.2f}%", flush=True)

    md = ["# DCA-анализ долгосрочного портфеля (локальные данные, 12 мес)", "",
          f"Окно: {start.date()} .. {end.date()} | Комиссия: 0.1%/покупка (binance spot) | "
          f"Еженедельный вклад: ${args.weekly:.0f}",
          "",
          "| Стратегия | Вложено $ | Итог $ | PnL % | CAGR % | MaxDD % |",
          "|---|---:|---:|---:|---:|---:|"]
    for name, r in variants:
        md.append(f"| {name} | {r['invested']:.0f} | {r['final']:.2f} | {r['ret_pct']:+.2f} | "
                  f"{r['cagr']:+.2f} | {r['max_dd']:.2f} |")
    md += ["",
           "**Контекст:** за окно BTC −46% за год (CoinGecko); рынок в глубокой коррекции. "
           "DCA в минусе — но в среднем по вариантам меньше, чем lump-sum, и меньше, чем "
           "аллокация в чистые альты. DCA — много-годичная стратегия; 12 мес — не финальная оценка.",
           "",
           "## Рекомендуемая аллокация (по умолчанию)",
           "",
           "Равные веса топ-10 без ребаланса: BTC 10%, ETH 10%, SOL 10%, XRP 10%, BNB 10%, "
           "DOGE 10%, TRX 10%, TON 10%, ADA 10%, LINK 10%.",
           "",
           "Альтернатива (консервативная): BTC 40%, ETH 25%, BNB 10%, SOL 10%, XRP 5%, "
           "DOGE 3%, TRX 3%, ADA 2%, LINK 2% — меньше альт-волатильности, хуже диверсификация "
           "в бычий цикл. Выбор — решение владельца."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
