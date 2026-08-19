#!/usr/bin/env python3
"""Ежедневный режимный движок: индикаторы → режим → latest + история.

Источники (только локальные данные, без сети):
- 1h-история BTC/ETH и вселенной (33 актива) из data/quant/<SYM>/*/*_1h.csv;
- Fear&Greed из data/quant/market_context_latest.json (если есть).

Пишет data/reports/market_regime_latest.json (для политики и отчётов)
и дописывает data/reports/market_regime_history.jsonl.

Usage: python scripts/quant_regime_engine.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
QUANT_DIR = REPO_ROOT / "data" / "quant"

from aios_core.quant.market_regime import (  # noqa: E402
    append_history,
    classify_regime,
    regime_payload,
    write_latest,
)

LATEST = REPO_ROOT / "data" / "reports" / "market_regime_latest.json"
HISTORY = REPO_ROOT / "data" / "reports" / "market_regime_history.jsonl"


def _daily(symbol: str) -> pd.Series | None:
    """UTC-дневные закрытия из самой длинной свежей 1h-серии."""

    import time

    cutoff = time.time() * 1000 - 7 * 86_400_000
    best, best_n = None, -1
    for cand in sorted(QUANT_DIR.glob(f"{symbol}/*/{symbol}_1h.csv")):
        try:
            df = pd.read_csv(cand, usecols=["timestamp_ms", "close"])
            if int(df["timestamp_ms"].max()) < cutoff:
                continue
            if len(df) > best_n:
                best, best_n = cand, len(df)
        except Exception:
            continue
    if best is None:
        return None
    df = pd.read_csv(best)
    df["ts"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
    return df.groupby(df["ts"].dt.date)["close"].last()


def breadth(daily: dict[str, pd.Series], days: int = 7) -> float | None:
    rets = []
    for sym, s in daily.items():
        if sym == "BTC" or len(s) < days + 1:
            continue
        rets.append(float(s.iloc[-1] / s.iloc[-1 - days] - 1.0) > 0)
    return float(np.mean(rets)) if rets else None


def main() -> int:
    universe = sorted(p.parent.parent.name
                      for p in QUANT_DIR.glob("*/binance/*_1h.csv"))
    daily = {}
    for sym in universe:
        s = _daily(sym)
        if s is not None and len(s) > 30:
            daily[sym] = s

    i: dict[str, float | None] = {}
    btc = daily.get("BTC")
    eth = daily.get("ETH")
    if btc is not None and len(btc) >= 200:
        close = btc.values
        i["btc_above_sma200"] = 1.0 if close[-1] > close[-200:].mean() else 0.0
        i["btc_above_sma50"] = 1.0 if close[-1] > close[-50:].mean() else 0.0
        i["btc_ret_7d_pct"] = round(float(close[-1] / close[-8] - 1.0) * 100, 2) if len(close) > 8 else None
        i["dd90_pct"] = round(float(close[-1] / close[-90:].max() - 1.0) * 100, 2) if len(close) >= 90 else None
        rets = np.diff(np.log(close[-31:]))
        i["vol30_annualized_pct"] = round(float(rets.std() * np.sqrt(365)) * 100, 1) if len(rets) > 5 else None
    if eth is not None and len(eth) >= 8:
        i["eth_btc_7d"] = round(float((eth.iloc[-1] / eth.iloc[-8]) / (btc.iloc[-1] / btc.iloc[-8]) - 1.0) * 100, 2) if btc is not None and len(btc) >= 8 else None
    i["breadth_7d"] = round(breadth(daily), 3) if len(daily) > 5 else None
    try:
        ctx = json.loads((QUANT_DIR / "market_context_latest.json").read_text(encoding="utf-8"))
        fng = (ctx.get("fng") or {}).get("value")
        i["fear_greed"] = float(fng) if fng is not None else None
    except Exception:
        i["fear_greed"] = None

    regime = classify_regime(i)
    payload = regime_payload(i, regime)
    write_latest(payload, LATEST)
    append_history(payload, HISTORY)
    print(f"regime={regime} risk={payload['risk_level']} strategy={payload['strategy_family']}")
    print("indicators:", json.dumps(i, ensure_ascii=False))
    print(f"latest -> {LATEST} | history -> {HISTORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
