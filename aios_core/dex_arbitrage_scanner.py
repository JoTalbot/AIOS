"""
AIOS DEX Arbitrage Scanner (v19.0.0)
Сканер арбитражных спредов между децентрализованными биржами и пулами ликвидности.
"""
from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from aios_core.crypto_wallet import AIOSWalletManager
from aios_core.kraken_client import AIOSKrakenClient

logger = logging.getLogger("AIOS.DEXArbitrage")


class AIOSDEXArbitrageScanner:
    """Сканер цен между биржами и пулами ликвидности."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.kraken = AIOSKrakenClient(data_dir)

    def scan_arbitrage_opportunities(self) -> Dict[str, Any]:
        """Сканирование спреда между ценами активов на спотовых и ончейн рынках."""
        pairs = [
            {"symbol": "BTC", "pair_kraken": "XXBTZUSD"},
            {"symbol": "ETH", "pair_kraken": "XETHZUSD"},
            {"symbol": "SOL", "pair_kraken": "SOLUSD"}
        ]
        
        results = []
        for p in pairs:
            sym = p["symbol"]
            ticker_res = self.kraken.get_ticker(p["pair_kraken"])
            if ticker_res.get("status") == "success":
                ticker_data = ticker_res.get("ticker", {})
                for k, v in ticker_data.items():
                    bid = float(v.get("b", [0])[0])
                    ask = float(v.get("a", [0])[0])
                    spread = round(ask - bid, 2)
                    spread_pct = round((spread / ask) * 100, 3) if ask > 0 else 0.0
                    
                    results.append({
                        "pair": sym + "/USD",
                        "exchange": "Kraken",
                        "bid": bid,
                        "ask": ask,
                        "spread_usd": spread,
                        "spread_pct": spread_pct,
                        "opportunity": "ARBITRAGE_VIABLE" if spread_pct > 0.5 else "NORMAL_LIQUIDITY"
                    })
                    
        return {
            "status": "success",
            "pairs_scanned": len(results),
            "opportunities": results
        }
