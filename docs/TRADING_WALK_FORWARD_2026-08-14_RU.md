# Directional v2 Walk-forward — 2026-08-14

## Методика

- Полностью offline, публичная сеть и ордера не используются.
- 35 активов, по одному приоритетному exchange dataset.
- Закрытые 1h OHLCV, обычно 500 свечей.
- 70% train: выбор SMA/RSI/TP/SL параметров.
- 30% строго out-of-sample: итоговая оценка.
- Cost model на каждой стороне: taker fee 0.15% + half-spread 0.05% + slippage 0.05%.
- Round-trip cost около 0.50%.

## Результат OOS

- Активов: 35.
- Положительных: 12/35 (34.3%).
- Средний net return: −0.354%.
- Median net return: −0.248%.
- Закрытых сделок: 115.
- Wins: 29; win-rate 25.2%.
- Aggregate profit factor: 0.374.
- Лучший: WIF/Kraken +0.510%.
- Худший: UNI/Kraken −1.608%.

## Вывод

Текущая technical directional стратегия не имеет положительной OOS expectancy после costs. Она не проходит обязательные gates:

- average return >0;
- positive assets ≥50%;
- 30 paper days;
- 200 closes;
- positive realized PnL;
- profit factor ≥1.20.

`AIOS_QUANT_ENTRY_MODE` остаётся `freeze`; live запрещён.

## Следующие гипотезы для исследования

1. Убрать принудительный bearish exit без подтверждённого expected edge.
2. Добавить regime filter: trend/volatility/liquidity.
3. Тестировать меньший universe и некоррелированные активы.
4. Использовать rolling multi-fold walk-forward вместо одного split.
5. Добавить bid/ask history, если доступна, вместо постоянной spread-оценки.
6. Сравнить directional v2 с monitoring-only и arbitrage-only paper baseline.

Нельзя подбирать параметры на OOS-сегменте. Любая следующая версия получает новый untouched test window.
