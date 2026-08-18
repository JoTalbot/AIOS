#!/usr/bin/env python3
"""Top-10 basket paper benchmark (Edge Lab 2026-08-17).

The scoreboard winner (equal-weight top-10 majors basket) as a daily
mark-to-market paper tracker: monthly rebalance to equal weights, 0.1%
fee per rebalance leg, values appended to data/reports/basket_paper.jsonl.
Read-only; uses the same 1h data as the quant universe.

Usage:
    python scripts/run_basket_paper.py [--state data/reports/basket_paper_state.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
QUANT_DIR = REPO_ROOT / "data" / "quant"

TOP10 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "TRX", "TON", "ADA", "LINK"]
START_CAPITAL = 1000.0
FEE = 0.001
STATE_FILE = REPO_ROOT / "data" / "reports" / "basket_paper_state.json"
HISTORY_FILE = REPO_ROOT / "data" / "reports" / "basket_paper.jsonl"


def newest_csv(symbol: str) -> Path | None:
    """CSV с самым свежим баром среди всех бирж (TON: binance делистнут
    30.06 — используется kraken)."""

    candidates = sorted(QUANT_DIR.glob(f"{symbol}/*/{symbol}_1h.csv"))
    best: Path | None = None
    best_ts = -1
    for cand in candidates:
        try:
            df = pd.read_csv(cand, usecols=["timestamp_ms"])
            ts = int(df["timestamp_ms"].max())
        except Exception:
            continue
        if ts > best_ts:
            best, best_ts = cand, ts
    return best


def longest_fresh_csv(symbol: str, freshness_days: int = 7) -> Path | None:
    """Самая длинная серия среди бирж со свежим баром (за freshness_days).

    Для волатильности важна длина истории, а не самый свежий бар
    (TON: kraken 33 дня vs bitstamp 26 — оба свежие, kraken длиннее).
    Делистнутые серии (например TON/binance, заканчивается 30.06)
    автоматически отсеиваются фильтром свежести.
    """

    import time

    cutoff = time.time() * 1000 - freshness_days * 86_400_000
    best: Path | None = None
    best_n = -1
    for cand in sorted(QUANT_DIR.glob(f"{symbol}/*/{symbol}_1h.csv")):
        try:
            df = pd.read_csv(cand, usecols=["timestamp_ms"])
            ts = int(df["timestamp_ms"].max())
        except Exception:
            continue
        if ts >= cutoff and len(df) > best_n:
            best, best_n = cand, len(df)
    return best


def _daily_closes_frame(symbol: str) -> pd.Series | None:
    path = longest_fresh_csv(symbol)
    if path is None:
        return None
    df = pd.read_csv(path)
    df["day"] = pd.to_datetime(df["timestamp_ms"], unit="ms").dt.strftime("%Y-%m-%d")
    return df.groupby("day")["close"].last()


def daily_close(symbol: str, day: str) -> float | None:
    """Last 1h close on or before `day` (YYYY-MM-DD) на свежайшей бирже."""

    frame = _daily_closes_frame(symbol)
    if frame is None:
        return None
    sel = frame[frame.index <= day]
    if sel.empty:
        return None
    return float(sel.iloc[-1])


def daily_closes(symbol: str, limit: int | None = None) -> list[float] | None:
    """Последние дневные закрытия (для волатильности)."""

    frame = _daily_closes_frame(symbol)
    if frame is None:
        return None
    if limit is not None:
        frame = frame.tail(limit)
    return [float(v) for v in frame.values]


def inverse_vol_weights(series: dict[str, list | None], window: int = 30) -> dict[str, float]:
    """Веса ∝ 1/σ дневных доходностей за `window` дней (чистая функция).

    Символ без достаточной истории получает вес 0; если волатильность не
    определена ни у кого — равные веса.
    """

    import numpy as np

    vols: dict[str, float | None] = {}
    for sym, closes in series.items():
        if not closes or len(closes) < window + 1:
            vols[sym] = None
            continue
        rets = np.diff(np.log(np.asarray(closes[-(window + 1):], dtype=float)))
        std = float(rets.std())
        vols[sym] = std if std > 0 else None
    known = {s: v for s, v in vols.items() if v is not None}
    if not known:
        n = max(1, len(series))
        return {s: 1.0 / n for s in series}
    inv = {s: 1.0 / vol for s, vol in known.items()}
    total = sum(inv.values())
    weights = {s: inv[s] / total for s in inv}
    for s in series:
        if s not in weights:
            weights[s] = 0.0
    return weights


def mark(state: dict, day: str) -> dict | None:
    """Compute basket value at `day`; returns None when data incomplete."""

    prices = {}
    for sym in TOP10:
        px = daily_close(sym, day)
        if px is None:
            return None
        prices[sym] = px
    value = state.get("cash_usd", 0.0) + sum(
        state["holdings"].get(sym, 0.0) * px for sym, px in prices.items())
    return {"day": day, "value_usd": round(value, 2), "prices": prices}


def rebalance(state: dict, day: str, prices: dict[str, float],
              weights: dict[str, float] | None = None) -> dict:
    """Monthly rebalance to target weights (fee per traded leg, honest cash
    flow). weights=None -> equal weights. On the first rebalance the whole
    cash is invested."""

    if weights is None:
        weights = {sym: 1.0 / len(prices) for sym in prices}
    value = state.get("cash_usd", 0.0) + sum(
        state["holdings"].get(sym, 0.0) * prices[sym] for sym in prices)
    if value <= 0 and state.get("cash_usd", 0.0) > 0:
        value = state["cash_usd"]
        state["cash_usd"] = 0.0
    fees = 0.0
    holdings = {}
    cash = state.get("cash_usd", 0.0)
    for sym, px in prices.items():
        qty = state["holdings"].get(sym, 0.0)
        target_qty = value * weights.get(sym, 0.0) / px
        diff = target_qty - qty
        traded = abs(diff) * px
        fees += traded * FEE
        cash -= diff * px  # покупки тратят кэш, продажи возвращают
        holdings[sym] = target_qty
    cash -= fees
    state["holdings"] = holdings
    state["cash_usd"] = cash
    state["fees_paid_usd"] = state.get("fees_paid_usd", 0.0) + fees
    state["last_rebalance"] = day
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", type=Path, default=STATE_FILE)
    ap.add_argument("--history", type=Path, default=HISTORY_FILE)
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
    else:
        state = {
            "start_capital": START_CAPITAL,
            "cash_usd": START_CAPITAL,
            "holdings": {},
            "fees_paid_usd": 0.0,
            "last_rebalance": None,
            "started": today,
        }

    row = mark(state, today)
    if row is None:
        print("SKIP: неполные данные по корзине", flush=True)
        return 0

    # ежемесячный ребаланс: в первый прогон нового месяца (или самый первый)
    if state["last_rebalance"] is None or today[:7] != state["last_rebalance"][:7]:
        vol_series = {sym: daily_closes(sym, limit=31) for sym in TOP10}
        weights = inverse_vol_weights(vol_series)
        rebalance(state, today, row["prices"], weights)
        state["weights_rule"] = "inverse_vol_30d"
        row = mark(state, today)

    state["updated"] = today
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    entry = {
        "day": today,
        "value_usd": row["value_usd"],
        "fees_paid_usd": round(state.get("fees_paid_usd", 0.0), 4),
        "invested_usd": state["start_capital"],
        "pnl_pct": round((row["value_usd"] / state["start_capital"] - 1) * 100, 3),
    }
    with args.history.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
