# AIOS Quant & RL — Руководство

Сводка по созданным в процессе развития компонентам: модели, скрипты, команды, автоматизация.

---

## Модели (data/quant/models/)

| Модель | Тип | Размер | Описание |
|---|---|---|---|
| `ppo_v4.pt` | **LSTM-PPO** (лучшая) | 193КБ | RL-агент на 32 активах, LSTM-слой, 100 эпизодов. Валидация: **RL +8.46% vs Buy&Hold -60.61%** |
| `ppo_v3.pt` | MLP-PPO | 160КБ | Мультиактив PPO (43 признака) |
| `ppo_multi_24.pt` | MLP-PPO | 99КБ | Мультиактив PPO (24 актива) |
| `ppo_trader.pt` | PPO (base) | 26КБ | Одиночный PPO (BTC) |
| `catboost_price_dir.cbm/.pkl` | CatBoost | 232КБ | ML-предсказание направления |
| `lstm_price_dir.pt` | LSTM (ML) | 25КБ | LSTM для ML-инференса |

## Скрипты

### RL-обучение (Kaggle)
- **`make_rl_v5.py` / `make_rl_v6.py`** — генераторы ноутбуков для Kaggle (GPU/CPU)
- Ноутбуки: `jotalbot/aios-rl-v4-2` (лучший CPU), `aios-rl-v5` (GPU), `aios-rl-v6` (CPU 200 эп)
- Запуск: `kaggle kernels push -p data/kg_v6`

### RL-мост
- **`aios_core/quant/rl_signal_bridge.py`** — загружает PPO-модель, предсказывает позиции (0/0.5/1)
- Поддерживает MLP и LSTM архитектуры
- Кеш сигналов на 5 мин (модель загружается 1 раз за цикл)
- CLI: `python aios_core/quant/rl_signal_bridge.py --save`

### ML-мост
- **`aios_core/quant/ml_signal_bridge.py`** — читает `ml_signals.json` (CatBoost), сильные сигналы

### Бэктест
- **`aios_core/quant/backtest_ai_strategies.py`** — Sharpe, Sortino, max DD, win rate
- `python aios_core/quant/backtest_ai_strategies.py --symbol BTC`
- Сводный: `scripts/export_reports_to_drive.py`

### Трейдинг
- **`run_quant_trading.py`** — демон трейдинга (10 бирж)
- **`aios_core/quant_trading_engine.py`** — движок, ML/RL-фактор в решениях
- Сброс демо-счетов: `reset_multi_exchange_demo()`

### RAG
- **`aios_ask.py`** — RAG-поиск по проекту + чатам + профилю + LLM-ответ
- `scripts/build_personal_knowledge.py` — сбор личной базы (чаты + профиль)
- `scripts/build_fastembed_collection.py` — эмбеддинги мультиязычной моделью

### Бэкап / утилиты
- `scripts/backup_to_drive.py` — бэкап на Google Диск (AIOS_backup)
- `scripts/cleanup_disk.py` — очистка диска
- `scripts/upload_gdrive.py` — загрузка на Google Диск (обход rate-limit)

## Команды Telegram
| Команда | Назначение |
|---|---|
| `/ask <вопрос>` | RAG-поиск по проекту/чатам/профилю (LLM-ответ) |
| `/signals` | ML + RL консультирующие сигналы |
| `/backtest <символ>` | Бэктест стратегии с метриками |

## Автоматизация (systemd timers)
| Timer | Расписание | Назначение |
|---|---|---|
| `aios-kaggle-retrain` | пн 04:00 | авто-переобучение RL через Kaggle |
| `aios-rag-refresh` | ежедневно 03:00 | обновление RAG-базы |
| `aios-report-export` | ежедневно 04:30 | экспорт отчётов на диск |
| `aios-gdrive-backup` | ежедневно 05:00 | бэкап важных данных на диск |
| `aios-local-backup` | ежедневно 03:30 | локальный бэкап |

## Мониторинг
- **Prometheus** :9090, **Grafana** :3000 (docker)
- Метрики: `aios_service_up` (api/mcp/grafana/prometheus/dashboard/ssh), `aios_auto_promotes_total`
- Экспортер: aios-exporter читает textfile из aios-api

## Биржи (демо $1000 каждая)
Kraken, Binance, Bybit, OKX, Uniswap V3, **Coinbase, KuCoin, Bitfinex, Bitstamp, MEXC** (итого $10000)

## Google Диск
- `AIOS_colab_models` — модели + результаты
- `AIOS_backup` — резервные копии (БД, конфиг, модели)
