"""
AIOS Smart Liquidity Router (v19.0.0)
Интеллектуальный маршрутизатор ликвидности и оптимизатор доходности DeFi между сетями.
"""
from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from web3 import Web3

from aios_core.crypto_wallet import AIOSWalletManager, PUBLIC_RPC_NODES
from aios_core.treasury_manager import AIOSTreasuryManager

logger = logging.getLogger("AIOS.LiquidityRouter")


class AIOSSmartLiquidityRouter:
    """Маршрутизатор ликвидности между сетями (Polygon, Base, Arbitrum)."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.treasury_mgr = AIOSTreasuryManager(data_dir)
        self.wallet_mgr = AIOSWalletManager(data_dir)

    def scan_multi_chain_yields(self) -> Dict[str, Any]:
        """Сравнительный анализ процентных ставок Lending APY по всем поддерживаемым сетям."""
        treasury_rates = self.treasury_mgr.check_defi_yields()
        
        # Получаем живые ставки
        poly_aave_usdt = treasury_rates.get("polygon_aave_v3_usdt_apy", 2.63)
        base_compound_usdc = treasury_rates.get("base_compound_v3_usdc_apy", 5.25)
        
        # Arbitrum Aave V3 APY (ориентир / on-chain query)
        arbitrum_aave_usdc = 4.15
        
        opportunities = [
            {
                "network": "Base",
                "protocol": "Compound V3",
                "asset": "USDC",
                "apy_pct": base_compound_usdc,
                "risk_score": "LOW",
                "gas_cost_usd": 0.01
            },
            {
                "network": "Arbitrum",
                "protocol": "Aave V3",
                "asset": "USDC",
                "apy_pct": arbitrum_aave_usdc,
                "risk_score": "LOW",
                "gas_cost_usd": 0.02
            },
            {
                "network": "Polygon",
                "protocol": "Aave V3",
                "asset": "USDT",
                "apy_pct": poly_aave_usdt,
                "risk_score": "LOW",
                "gas_cost_usd": 0.01
            }
        ]
        
        opportunities.sort(key=lambda x: x["apy_pct"], reverse=True)
        best_opportunity = opportunities[0]
        
        # Расчет свободных средств казначейства
        audit = self.treasury_mgr.audit_reserves()
        excess_usd = audit.get("excess_funds_available_usd", 0.0)
        
        # Расчет прогнозной годовой доходности
        annual_yield_usd = round(excess_usd * (best_opportunity["apy_pct"] / 100.0), 2)
        
        return {
            "status": "success",
            "best_yield_strategy": best_opportunity,
            "all_opportunities": opportunities,
            "available_excess_capital_usd": excess_usd,
            "estimated_annual_yield_usd": annual_yield_usd,
            "rebalance_action_required": best_opportunity["network"] != "Polygon" and excess_usd >= 20.0
        }
