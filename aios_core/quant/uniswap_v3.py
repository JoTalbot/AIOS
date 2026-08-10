#!/usr/bin/env python3
"""
AIOS Quant ML Engine - Данные Uniswap V3 через DefiLlama (Этап 2.1)

Uniswap V3 не поддерживается ccxt, а legacy The Graph hosted subgraph выключен.
Поэтому используем бесплатный публичный API DefiLlama (без ключей):

  - /protocol/uniswap          -> TVL по сетям, комиссии, объёмы протокола
  - /overview/dexs             -> агрегированные объёмы DEX по сетям
  - /coins/llama.fi/prices/... -> текущие цены активов

ВАЖНО: глубокие пул-свечи (OHLCV по конкретным пулам) из бесплатного
DefiLlama не отдаются. Для этого нужен API-ключ The Graph gateway
(см. .env: ключа нет). Поэтому модуль даёт on-chain статистику ликвидности
и объёмов Uniswap, а исторические свечи для обучения берутся с CEX-бирж
(data_collector.py), которые полностью покрывают 24 актива.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
QUANT_DIR = REPO_ROOT / "data" / "quant"

LLAMA_BASE = "https://api.llama.fi"
COINS_BASE = "https://coins.llama.fi"

LOG_TAG = "[UniswapV3]"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, timeout: int = 25) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"{LOG_TAG} [WARN] {url}: {e}")
        return None


class UniswapV3Collector:
    """Сбор on-chain данных Uniswap V3 через DefiLlama."""

    def __init__(self, quant_dir: Optional[Path] = None):
        self.quant_dir = Path(quant_dir or QUANT_DIR)
        self.quant_dir.mkdir(parents=True, exist_ok=True)

    def fetch_protocol_stats(self) -> Optional[dict]:
        """TVL по сетям, объёмы, комиссии протокола Uniswap."""
        d = _get(f"{LLAMA_BASE}/protocol/uniswap")
        if not d:
            return None
        return {
            "name": d.get("name"),
            "chains_tvl": d.get("currentChainTvls"),
            "chain_tvls": d.get("chainTvls"),
            "current_tvl": d.get("currentTvl"),
            "cumulative_volume": d.get("cumulativeVolume"),
            "fee_volume": d.get("currentVolume"),
            "collected_at": _utc_now(),
        }

    def fetch_dex_volume(self, chain: str = "ethereum", days: int = 7) -> Optional[list]:
        """История объёма DEX Uniswap по сети (первые `days` записей из totalDataChart)."""
        d = _get(
            f"{LLAMA_BASE}/overview/dexs/uniswap"
            "?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"
        )
        if not d or not isinstance(d, dict):
            return None
        chart = d.get("totalDataChart") or []
        return chart[-days:] if chart else []

    def fetch_prices(self, symbols: list[str]) -> dict:
        """Текущие цены активов (coingecko через DefiLlama)."""
        ids = ",".join(f"coingecko:{s.lower()}" for s in symbols)
        d = _get(f"{COINS_BASE}/prices/current/{ids}")
        if not d:
            return {}
        out = {}
        for k, v in (d.get("coins") or {}).items():
            sym = k.split(":")[-1].upper()
            out[sym] = {"price": v.get("price"), "confidence": v.get("confidence"),
                        "timestamp": v.get("timestamp")}
        return out

    def collect_all(self, symbols: Optional[list[str]] = None, save: bool = True) -> dict:
        summary = {}
        stats = self.fetch_protocol_stats()
        if stats:
            summary["protocol_tvl_chains"] = len(stats.get("chains_tvl") or {})
            summary["current_tvl_usd"] = stats.get("current_tvl")
        if save and stats:
            d = self.quant_dir / "uniswap_v3"
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "protocol_stats.json", "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

        if symbols:
            prices = self.fetch_prices(symbols)
            summary["prices"] = prices
            if save:
                d = self.quant_dir / "uniswap_v3"
                d.mkdir(parents=True, exist_ok=True)
                with open(d / "prices.json", "w", encoding="utf-8") as f:
                    json.dump({"collected_at": _utc_now(), "prices": prices},
                              f, indent=2, ensure_ascii=False)
        return summary


if __name__ == "__main__":
    import sys
    c = UniswapV3Collector()
    symbols = sys.argv[1:] or ["BTC", "ETH", "SOL", "UNI"]
    print(json.dumps(c.collect_all(symbols=symbols), indent=2, ensure_ascii=False)[:2000])
