"""
AIOS Web3 Gas Sentry & Transaction Cost Optimizer
Модуль мониторинга стоимости газа (Gas Price) и защиты казначейства от перегрузок блокчейна.
"""
from __future__ import annotations

import os
import logging
from typing import Dict, Any
from web3 import Web3

logger = logging.getLogger("AIOS.GasSentry")

# Максимальные допустимые пороги газа во избежание потерь бюджета (в Gwei)
MAX_GAS_LIMITS_GWEI = {
    "polygon": 120.0,  # Защитный лимит для Polygon (обычно нормальный газ ~30-80 Gwei)
    "base": 2.5        # Защитный лимит для Base (нормальный газ ~0.01-0.1 Gwei)
}


class Web3GasSentry:
    """Сторож стоимости газа в сетях EVM."""

    @staticmethod
    def get_current_gas_price_gwei(w3: Web3, network: str = "polygon") -> float:
        """Получает текущую стоимость газа в Gwei."""
        try:
            gas_price_wei = w3.eth.gas_price
            gas_price_gwei = w3.from_wei(gas_price_wei, 'gwei')
            return float(gas_price_gwei)
        except Exception as e:
            logger.error(f"Ошибка получения Gas Price для {network}: {e}")
            return 999999.0 # Возвращаем бесконечный газ при сбое

    @classmethod
    def is_gas_safe(cls, w3: Web3, network: str = "polygon") -> Dict[str, Any]:
        """Проверяет, безопасна ли текущая комиссия для отправки транзакции."""
        current_gas = cls.get_current_gas_price_gwei(w3, network)
        max_allowed = MAX_GAS_LIMITS_GWEI.get(network.lower(), 150.0)
        
        is_safe = current_gas <= max_allowed
        
        return {
            "network": network,
            "is_safe": is_safe,
            "current_gas_gwei": round(current_gas, 2),
            "max_allowed_gwei": max_allowed,
            "status": "safe" if is_safe else "congested"
        }
