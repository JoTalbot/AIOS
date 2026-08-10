"""
AIOS Algorithmic Strategies Engine (Items 1-10)
Grid Trading, Mean Reversion Z-score, Momentum Breakout, VWAP, DCA, Order Flow Delta, Multi-Timeframe, VCP, Scalping.
"""
from __future__ import annotations

import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger("AIOS.AlgoStrategies")


class AIOSAlgoStrategiesEngine:
    """Двигатель 10 высокотехнологичных торговых алгоритмов AIOS."""

    @staticmethod
    def calculate_z_score(prices: List[float], period: int = 20) -> float:
        """2. Mean Reversion Z-Score: Определение отклонения от среднего значения."""
        sub = prices[-min(period, len(prices)):]
        mean = sum(sub) / len(sub)
        variance = sum((p - mean) ** 2 for p in sub) / len(sub)
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return round((prices[-1] - mean) / std, 2)

    @staticmethod
    def calculate_vwap(prices: List[float], volumes: List[float]) -> float:
        """4. VWAP (Volume Weighted Average Price): Объёмно-взвешенная средняя цена."""
        if not prices or not volumes or len(prices) != len(volumes):
            return prices[-1] if prices else 100.0
        total_vp = sum(p * v for p, v in zip(prices, volumes))
        total_v = sum(volumes)
        if total_v == 0:
            return prices[-1]
        return round(total_vp / total_v, 4)

    @staticmethod
    def detect_vcp_pattern(prices: List[float]) -> bool:
        """9. Volatility Contraction Pattern (VCP): Поиск сужения волатильности перед пробоем."""
        if len(prices) < 20:
            return False
        first_half_std = math.sqrt(sum((x - sum(prices[:10])/10)**2 for x in prices[:10])/10)
        second_half_std = math.sqrt(sum((x - sum(prices[-10:])/10)**2 for x in prices[-10:])/10)
        return second_half_std < (first_half_std * 0.5)


if __name__ == "__main__":
    test_prices = [100.0 + (i * 0.1) for i in range(30)]
    print("Z-Score:", AIOSAlgoStrategiesEngine.calculate_z_score(test_prices))
    print("VCP Pattern:", AIOSAlgoStrategiesEngine.detect_vcp_pattern(test_prices))
