# F-2: funding-rate эксперимент — результат (отрицательный)

**Дата:** 2026-08-15 | **Скрипт:** `scripts/quant_ml_funding_experiment.py`
**Данные:** Binance Futures funding rate (публичный API, без ключа), 30 активов, 166 дней (8h начисления).

## Методика
- Funding на 1h-бары без lookahead: только начисления с fundingTime <= t (merge_asof, backward);
- фичи: f_last, f_24h_sum, f_7d_sum, f_7d_std, f_neg_frac7, f_30d_z, f_sign, f_extreme;
- CatBoost v2 (400/5/0.03), честный 70/30 gap 48; PnL — движок 1:1 (live config).

## Результаты
| Модель | AUC | hit@0.55 | cov@0.55 | Сделок | PnL $ |
|---|---:|---:|---:|---:|---:|
| cand_base (13 фич) | 0.5296 | 0.558 | 1.2% | — | — |
| cand_funding (13+8) | 0.5239 | 0.557 | 1.6% | 1 | −2.99 |
| deployed v2 (прод) | — | — | — | 33 | −5.86 |

Топ-фичи: funding-фичи почти без веса (лучшая f_7d_std — 1.3%, 14-е место).

## Вывод
Funding rate на 8h-начислениях не несёт edge для 1h-направления после издержек
(AUC не улучшается, PnL отрицательный). Гипотеза F-2 не подтверждена — правило
решения (AUC > base+0.005 И PnL > 0) не выполнено. 7-й отрицательный результат
(LONG OOS, SHORT OOS, ML-CS, prod-3m, tf×universe, MTF, funding).
OIS-история доступна только ~30 дней — для обучения не годится, начали копить.
