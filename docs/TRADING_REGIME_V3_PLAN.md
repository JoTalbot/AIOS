# Regime-filter Directional v3 — research contract

## Ограничение

`AIOS_QUANT_ENTRY_MODE=freeze`; live и новые paper entries запрещены до отдельного v3 gate. OOS-сегмент Directional v2 повторно для подбора не используется.

## Гипотеза

Directional edge оценивается только внутри рыночного режима:

- trend: slope SMA/EMA + ADX proxy;
- volatility: ATR/realized-vol percentile;
- liquidity: volume, spread и freshness;
- correlation: не более одной позиции на correlated cluster.

## Эксперимент

1. Расширить локальную 1h историю; 500 свечей недостаточно для устойчивых regime folds.
2. Rolling walk-forward минимум 4 folds: train → validation → untouched test.
3. Parameters выбираются внутри train/validation каждого fold; test никогда не участвует в выборе.
4. Universe: только ликвидные активы с полными данными во всех folds.
5. Cost model: fee 0.15%/side + исторический/консервативный spread + slippage.
6. Сравнить с baselines: buy-and-hold, monitoring/no-trade и Directional v2.

## Gate v3

- минимум 4 OOS folds и 1,000 совокупных OOS bars на актив;
- median OOS net return >0;
- positive folds ≥75%;
- aggregate PF ≥1.20;
- Sharpe ≥1.0;
- max drawdown ≤3%;
- ≥200 OOS closes;
- устойчивость при costs ×1.5;
- затем отдельные 30 дней paper, только после owner approval.

## Запреты

- не подбирать параметры на v2 OOS;
- не включать entries ради накопления sample до прохождения historical v3 gate;
- не использовать theoretical arbitrage как прибыль;
- не переходить в live автоматически.
