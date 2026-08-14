# AIOS Trading Research Comparison

Runtime decision: **monitoring-only**. Quant executor disabled; no paper/live entries.

| Direction | OOS result | Decision |
|---|---:|---|
| Directional v2 | average −0.354%, PF 0.374 | reject |
| Regime v3 | median −0.754%, positive folds 8.9% | reject |
| 1h arbitrage | −$0.506, 1 trade | reject |
| Cross-sectional | median −8.664%, positive 33.3% | reject |
| Pairs | median −13.161%, positive 33.3% | reject |
| Low-frequency trend | median −2.747%, positive 16.7% | reject |
| Market-making | недостаточно snapshots | collect data |
| DeFi yield | zero live balance, mock destination, stub bridge | blocked |

Ни одна стратегия не прошла comparative gate. Разрешены только market-data, ML, Signal Monitor и orderbook research collector.
