# Regime-filter Directional v3 — результат 2026-08-14

## Данные и метод

- 15 ликвидных активов, приоритет Kraken/Binance/KuCoin/Bitstamp/MEXC.
- 5 000 закрытых 1h свечей на dataset.
- Causal features: EMA slope, trend-strength proxy, ATR percentile, volume/range liquidity, freshness.
- Regimes: trend_up, trend_down, range, high_volatility, illiquid.
- Rolling folds: 2 000 train + 500 untouched OOS; 90 OOS folds суммарно.
- Costs: Directional v2; дополнительный stress test costs ×1.5.
- Correlation clusters рассчитаны по returns.

## Итог

- Median OOS net return: −0.754%.
- Positive fold ratio: 8.9%.
- Median OOS при costs ×1.5: −1.158%.

## Решение

Historical gate не пройден. `AIOS_QUANT_ENTRY_MODE=freeze` сохраняется; paper entries и live запрещены.

Текущие folds становятся исследованными и не могут использоваться для дальнейшего подбора параметров. Следующая гипотеза требует нового временного окна либо перехода к market-neutral/arbitrage-only исследованию.
