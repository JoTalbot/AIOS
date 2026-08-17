# AIOS Quant Signal Monitor

Read-only monitoring product: объединяет ML probability, RL position, market regime, freshness, ATR/volume percentile и выдаёт `WATCH_UP`, `WATCH_DOWN`, `NEUTRAL`, `NO_DATA`.

Не создаёт ордера, не меняет portfolio state и не отправляет сообщения.

Artifacts:

- `data/reports/quant_signal_product.json`;
- `data/reports/quant_signal_product.md`.

Запуск: `python scripts/generate_quant_signal_product.py`.

Hourly timer: `aios-quant-signal-product.timer`.

Первый запуск: 35 активов, 0 WATCH_UP, 1 WATCH_DOWN, 28 neutral, 6 no-data. Trading остаётся freeze.

Актуализация 2026-08-14 (paper-fix сессия):

- Мёртвые тикеры MATIC/RNDR (переименованы в POL/RENDER) исключены из сигналов: 35 → **33 актива**.
- Дособор истории до ~5000-5500 баров по всем 33 активам (`scripts/quant_backfill_history.py`, Binance + Bybit fallback для KAS).
- Выбор источника: самая полная **свежая** серия среди бирж (устаревшие >2h отбрасываются — делистинг TONUSDT на Binance 24.06 больше не затеняет живые bitstamp/kraken данные).
- Regime считается по последнему **закрытому** бару (незакрытый бар с частичным объёмом давал ложный `illiquid`): NO_DATA 16 → 0.
- ML-модель: scale-free CatBoost v2 (`catboost_price_dir_v2.cbm`), обучение `scripts/quant_ml_eval_train.py` — OOS AUC 0.536, hit@prob≥0.65 = 82.4%, симуляция по правилам Directional v2: +31.6% net (порог 0.65).
- RL-модель: PPO v9 (`ppo_v9.pt`), обучение `scripts/quant_train_ppo.py` (методология kg_v8, CPU) — sum_rl +96.0% vs Buy&Hold −114.0%; консервативный veto (все активы FLAT).
- Состояние на 2026-08-14 17:15Z: 33 сигнала, 0 NO_DATA, WATCH_DOWN: OP, PEPE.

## API pilot

`GET /api/v2/mon/quant-signals?label=WATCH_UP&limit=20` возвращает только сохранённый artifact, freshness и disclaimer. Endpoint не запускает модели и не имеет execution actions.
