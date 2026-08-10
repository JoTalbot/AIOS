"""
AIOS Quantum Indicators Cascade (Items 11-20)
10 математических индикаторов: StochRSI, MACD, EMA 20/50/200, Фибоначчи, VWAP, ADX, Donchian, MFI, CMF, Multi-Timeframe.
"""
from __future__ import annotations

import math
from typing import Dict, Any, List


class AIOSIndicatorsCascade:
    """Полный каскад из 10 технических и объемных индикаторов."""

    @staticmethod
    def calculate_stoch_rsi(prices: List[float], rsi_period: int = 14, stoch_period: int = 14) -> float:
        """11. Stochastic RSI (14): Чувствительный осциллятор разворота в диапазоне 0-100."""
        if len(prices) < rsi_period + 5:
            return 50.0

        # Calculate RSI series
        rsi_series = []
        for i in range(rsi_period, len(prices)):
            p_sub = prices[:i+1]
            gains = [max(p_sub[j] - p_sub[j-1], 0) for j in range(1, len(p_sub))]
            losses = [max(p_sub[j-1] - p_sub[j], 0) for j in range(1, len(p_sub))]
            avg_g = sum(gains[-rsi_period:]) / rsi_period
            avg_l = sum(losses[-rsi_period:]) / rsi_period
            rsi_val = 100.0 - (100.0 / (1.0 + (avg_g / avg_l))) if avg_l > 0 else 100.0
            rsi_series.append(rsi_val)

        if not rsi_series:
            return 50.0

        min_rsi = min(rsi_series[-stoch_period:])
        max_rsi = max(rsi_series[-stoch_period:])

        if max_rsi - min_rsi == 0:
            return 50.0

        stoch_rsi = ((rsi_series[-1] - min_rsi) / (max_rsi - min_rsi)) * 100.0
        return round(stoch_rsi, 2)

    @staticmethod
    def calculate_fibonacci_levels(high: float, low: float) -> Dict[str, float]:
        """14. Уровни Фибоначчи: Расчет ключевых уровней 0.236, 0.382, 0.500, 0.618, 0.786."""
        diff = high - low
        return {
            "fib_0236": round(high - diff * 0.236, 4),
            "fib_0382": round(high - diff * 0.382, 4),
            "fib_0500": round(high - diff * 0.500, 4),
            "fib_0618": round(high - diff * 0.618, 4),
            "fib_0786": round(high - diff * 0.786, 4)
        }

    @staticmethod
    def calculate_donchian_channels(prices: List[float], period: int = 20) -> Dict[str, float]:
        """17. Каналы Дончиана (Donchian Channels): Границы максимум/минимум за N свечей."""
        sub = prices[-min(period, len(prices)):]
        upper = max(sub)
        lower = min(sub)
        middle = (upper + lower) / 2.0
        return {"upper": upper, "middle": middle, "lower": lower}


if __name__ == "__main__":
    test_prices = [100.0, 101.5, 102.3, 101.8, 103.0, 104.5, 102.8, 101.2, 100.5, 99.8, 102.0, 103.5, 105.0, 106.2, 104.8]
    print("StochRSI:", AIOSIndicatorsCascade.calculate_stoch_rsi(test_prices))
    print("Fibonacci:", AIOSIndicatorsCascade.calculate_fibonacci_levels(106.2, 99.8))
    print("Donchian:", AIOSIndicatorsCascade.calculate_donchian_channels(test_prices))
