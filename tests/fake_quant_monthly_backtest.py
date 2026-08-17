"""Fake quant_monthly_backtest for local testing: synthetic prices where news
sentiment correlates with 1h forward moves (deterministic, end-to-end check)."""
from __future__ import annotations

import numpy as np
import pandas as pd

START = pd.Timestamp("2025-09-01", tz="UTC")
HOURS = 8760
SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]


def _build(sym: str, bumps: dict[int, float]) -> pd.DataFrame:
    """bumps: hour-index -> daily multiplier applied from that hour on."""
    n = HOURS
    ts = [int((START + pd.Timedelta(hours=h)).timestamp() * 1000) for h in range(n)]
    close = np.full(n, 100.0)
    drift = 0.0001
    for h in range(1, n):
        b = bumps.get(h, drift)
        close[h] = close[h - 1] * (1.0 + b)
    df = pd.DataFrame({
        "timestamp_ms": ts,
        "open": close * 0.999,
        "high": close * 1.001,
        "low": close * 0.999,
        "close": close,
        "volume": np.full(n, 1000.0),
    })
    return df


def load_symbols(venue: str = "binance"):
    """Return synthetic prices. Bumps are injected by the test before calling."""
    global _bumps
    bumps = globals().get("_bumps", {})
    out = {s: _build(s, bumps.get(s, {})) for s in SYMBOLS}
    used = {s: "binance" for s in SYMBOLS}
    return out, used


def set_bumps(bumps: dict[str, dict[int, float]]) -> None:
    globals()["_bumps"] = bumps
