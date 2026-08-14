# AIOS Quant Signal Monitor

Read-only monitoring product: объединяет ML probability, RL position, market regime, freshness, ATR/volume percentile и выдаёт `WATCH_UP`, `WATCH_DOWN`, `NEUTRAL`, `NO_DATA`.

Не создаёт ордера, не меняет portfolio state и не отправляет сообщения.

Artifacts:

- `data/reports/quant_signal_product.json`;
- `data/reports/quant_signal_product.md`.

Запуск: `python scripts/generate_quant_signal_product.py`.

Hourly timer: `aios-quant-signal-product.timer`.

Первый запуск: 35 активов, 0 WATCH_UP, 1 WATCH_DOWN, 28 neutral, 6 no-data. Trading остаётся freeze.
