# Макро + on-chain + деривативы: предсказательный тест — РЕЗУЛЬТАТ

**Дата:** 2026-08-16 | Скрипты: `fetch_market_data.py`, `fetch_derivatives.py`, `analyze_predictive.py`

## Методика (разработано и протестировано ЛОКАЛЬНО, потом деплой)
- Локальные тесты: `tests/macro/test_macro_pipeline.py` — 22 теста (парсинг Yahoo/blockchain/Binance,
  лаги без lookahead, синтетика с известной корреляцией, часовая нормализация): **22/22 PASS** локально
  и на сервере; всего 73 зелёных теста (22 макро + 30 новостей + 21 сентимент);
- Данные: 400 дней daily (Yahoo: DXY, SPX, NDX, IBIT, BTC-USD; blockchain.info: hashrate, n_tx,
  n_unique_addr, tx_vol_usd) + 720 часов деривативов Binance Futures (taker-buy-ratio, global/top
  Long-Short ratio, OI) + 1419 часовых цен BTC;
- Проверка: фича (t-1) -> доходность BTC за [t, t+1d] (daily) / [t, t+1h/4h/24h] (hourly);
- Лаги строго без lookahead (фича известна до начала окна доходности).

## Результаты
### Daily (400 дней): корреляции ≈ 0
| Фича | corr | Q20 | Q80 | diff |
|---|---:|---:|---:|---:|
| DXY | +0.039 | −0.16% | +0.16% | +0.32% |
| SPX / NDX / IBIT | ~0 | | | ≈0 |
| hashrate / n_tx / n_unique / tx_vol | <0.05 | | | ≈0 |

### Hourly (деривативы): единственный «сигнал» — LSR → 24h
| Фича | corr (все) | TRAIN corr | TEST corr | diff (test) |
|---|---:|---:|---:|---:|
| global_lsr → 24h | +0.199 | +0.171 | +0.439 | +0.97% |
| top_lsr → 24h | +0.182 | — | — | +0.83% |
| oi → 24h | +0.133 | — | — | +0.37% |
| taker_buy_ratio | ≈0 | | | |

### Проверка устойчивости (ключевой тест)
- LONG при LSR>мед: TRAIN +8.7% gross (BH +10.6%), TEST −34% (BH −72.6%) — убыточен в медвежьем;
- SHORT при LSR<мед: TRAIN **−1.9% gross / −35% net** (BH +10.6%) — УБЫТОК в бычьем;
  TEST +38% (BH −72.6%) — прибыль в медвежьем;
- По блокам по 100: SHORT +23%, +38%, **−22%**, +10% — знак зависит от режима рынка.

## Вывод
**LSR — это прокси режима рынка, а не предсказатель.** В бычьих фазах лонги доминируют
(LSR высок), в медвежьих — шорты (LSR низок); корреляция LSR→24h отражает тренд-продолжение.
Стратегия «шорт при низком LSR» зарабатывает ТОЛЬКО в медвежьем рынке — это тривиальный
режимный фильтр, не edge. После издержек и в смешанных периодах — убыток.

**10-й отрицательный результат** направленного предсказания (OHLCV, SHORT, ML-CS, MTF,
funding, горизонты, prod-3m, tf×universe, сентимент, макро/деривативы). Новых классов
данных для предсказания цены не осталось.

## Побочные продукты
- **LSR/OI/taker-накопитель** (`collect_derivatives_daily.py` + aios-derivatives-collector.timer,
  ежечасно): строит длинную историю деривативов (API-кап 500 записей) — через месяцы
  появится dataset для проверки LSR как ИНДИКАТОРА РЕЖИМА (для DCA-тайминга/фильтров);
- **Макро-монитор**: DXY/индексы/hashrate ежедневно в data/market_data — контекст для DCA;
- LSR добавлен в аналитику как индикатор режима, не как сигнал.

## Воспроизводимость
```bash
python scripts/tests/../tests/macro/test_macro_pipeline.py   # 22 теста
python scripts/fetch_market_data.py --out-dir data/market_data --days 400 --hourly
python scripts/fetch_derivatives.py --symbol BTC --hours 720 --out data/derivatives
python scripts/analyze_predictive.py --data-dir data/market_data --deriv data/derivatives
```
