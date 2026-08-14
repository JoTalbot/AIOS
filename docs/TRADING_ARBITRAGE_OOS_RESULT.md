# Arbitrage-only OOS — результат 2026-08-14

## Методика

- 15 активов, Binance/KuCoin/MEXC, 5 000 закрытых 1h свечей.
- Только синхронные USDT series; USD/USDT не смешиваются.
- Сигнал на свече `t`, исполнение по ценам `t+1` на тех же биржах.
- Fees 0.15%/side, slippage 0.10%/side; stress costs ×1.5.
- Rolling train 2 000 / untouched OOS 500; 90 folds.
- Cooldown 6 часов, pre-funded inventory assumption, $100 paper notional.

## Результат

- Исполнимых OOS trades: 1.
- Aggregate net PnL: −$0.506.
- Positive fold ratio: 0%.
- Median fold PnL: $0.
- Stress net PnL: −$0.755.

## Решение

Market-neutral cross-exchange edge на 1h close data не подтверждён. Arbitrage-only paper не переводится в runtime execution. Directional и live entries остаются frozen.

Следующее рациональное направление — monitoring/signal product либо сбор high-frequency orderbook snapshots для отдельного исследования; текущие OOS folds повторно для подбора не используются.
