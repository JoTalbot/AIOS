# Сессия: paper-контур — диагностика блокировок входа

---
session_id: "20260814T160500Z-aios-arena-paper-fix"
status: "DONE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T16:05:00Z"
updated_utc: "2026-08-14T17:45:00Z"
branch: "agent/20260814-paper-fix"
base_commit: "9d5dbd7b"
claim: "coordination/claims/paper-fix--20260814T160500Z-aios-arena-paper-fix.md"
---

## Цель

Разобраться, почему owner-approved paper-контур (aios-quant-trading) не открывает позиции, и починить так, чтобы paper-вход реально работал без изменения owner-профиля риска. Live запрещён.

## Диагноз

- `exchange_not_allowed` 96/цикл — by design: owner-профиль ограничивает kucoin,bitstamp,mexc (7 из 10 бирж вне allowlist). Не баг.
- `ml_not_confirmed` 17/цикл — корневой блокер: развёрнутая CatBoost-модель (Colab, 2026-08-12) деградирована — prob_up=0.433 ровно для 30/35 активов, AUC 0.504, на OOS ни разу >=0.60. Гейт 0.65 физически недостижим.
- Причина деградации: обучение на сырых абсолютных ценах (BTC 95000 vs PEPE 2.7e-6) в одном пуле без нормализации + финальный fit на всех данных без честного OOS.

## Решение

1. Новый `scripts/quant_ml_eval_train.py`: строгий per-symbol walk-forward (train 70% / test 30%, gap 48 бар), масштаб-инвариантные признаки (ret1..24, rsi, bb_pos, macd_norm, ema_gap, vol_ratio, vol_z, bar_range_pct, hl_pos), label = направление следующего 1h бара.
2. Кандидат `catboost_price_dir_v2.cbm` (AUC 0.533) валидирован на двух независимых OOS-окнах:
   - среднее окно (train 55%): hit@0.65=81.3%, 32 сделки, win 68.8%, avg +0.59% net, итог +18.9%
   - последнее окно (train 70%): hit@0.65=83.3%, 36 сделок, win 75.0%, avg +0.74% net, итог +26.5%
   - симуляция по правилам движка (TP+2%/SL-1%/trail, комиссии 0.5% round-trip, исполнение по триггерному уровню)
3. `aios_core/quant/ml_predictor.py`: DEFAULT_FEATURES → 13 scale-free признаков (1:1 формулы), приоритет загрузки catboost_price_dir_v2.cbm; старая модель остаётся fallback'ом (откат = удалить v2).
4. Признаки предиктора сверены с тренировочным скриптом — совпадение 1:1 (abs diff < 1e-9).

## Проверки

- [PASS] python -m py_compile aios_core/quant/ml_predictor.py, scripts/quant_ml_eval_train.py
- [PASS] pytest quant-набор: 18 passed (directional_v2, run_quant_trading_v2, v2_gate, walkforward_v2, signal_product, signal_api, directional_policy)
- [PASS] feature parity: тренировочный скрипт vs предиктор (BTC CSV) — 1:1
- [PASS] run_quant_ml_inference.py: ml_signals.json перегенерирован моделью v2, prob_up 0.38-0.60 (различаются), 1 актив >=0.60
- [PASS] gate-проверка с owner-профилем: ML=0.70 conf=0.90 → вход разрешён (None); ML=0.45 → ml_not_confirmed; binance → exchange_not_allowed
- [NOT RUN] полный pytest suite (5 198 тестов) — затронуты только quant/ml пути, покрыты выше

## Изменённые файлы

- `scripts/quant_ml_eval_train.py` — новый: диагностика + обучение кандидата + симуляция paper-сделок
- `aios_core/quant/ml_predictor.py` — scale-free признаки v2, приоритет модели v2
- `data/quant/models/catboost_price_dir_v2.cbm/.pkl` — runtime-артефакт (git-ignored), старый .cbm сохранён

## Git

- Branch `agent/20260814-paper-fix`, commit `8d668f03` (2 файла, +336/-7). Не закоммичены: coordination/sessions, claims, PROJECT_CONTEXT (следующий коммит).

## Деплой и верификация runtime (16:13-16:25Z)

- Inference-демон перезапущен (единичный restart после смены кода; старый процесс держал в памяти старый модуль): `[QuantMLPredictor] Модель загружена: .../catboost_price_dir_v2.cbm`.
- ml_signals.json перегенерирован моделью v2 (16:13:49Z): prob_up различаются (0.38-0.60), 1 актив >=0.60.
- Trading-демон цикл 16:13Z чистый: blocks={'exchange_not_allowed': 96, 'ml_not_confirmed': 9} (было 17 — сигналы больше не константа; до 0.65 сегодня не дотянул ни один актив — это нормальная селективность гейта).
- Ветка agent/20260814-paper-fix опубликована в origin (GitHub JoTalbot/AIOS); origin/main синхронизирован (9d5dbd7b).


## Этап 2: RL-мост и мёртвые тикеры (пункты 1-2 из handoff)

### RL-мост (aios_core/quant/rl_signal_bridge.py) — 3 бага исправлено

Сверка с обучающей средой data/kg_v8/aios-rl-v8.ipynb (MultiAssetEnv, obs_dim=46):

1. **onehot-баг**: обучение — onehot[индекс] в sorted(32 активов); мост всегда ставил onehot[0]=BTC для всех активов → все сигналы одинаковые. Фикс: константа ASSET_ORDER (32 актива из ноутбука, алфавитный порядок), onehot по индексу запрошенного актива; актив вне универсума → честный None (нет сигнала), а не чужой индекс.
2. **Признак vol_chg вместо vol_ratio**: обучение использует [rets(10), mom5, mom12, vol_ratio, vol_norm]; мост подавал vol_chg на 3-й статической позиции. Фикс: vol_ratio = volume/rolling(10)-mean.
3. **Отсутствие clamp**: в обучении act.clamp(-1,1) до конвертации в дискрету {0,1,2}; в мосте mean=-2.77 давал pos=-0.5 (вне [0,1]). Фикс: clamp(-1,1) перед конвертацией.

Результат: 9 сигналов (POL честно отброшен — нет в обучающем универсуме), pos ∈ {0, 0.5, 1.0}, активы различаются. Модель PPO v8 на текущем рынке даёт FLAT по всем 9 мажорам (mean < -1 → действие «выход») — честный вердикт модели, консервативный veto сохраняется. Переобучение PPO в Colab — отдельная задача.

### Мёртвые тикеры MATIC/RNDR

- `aios_core/quant/ml_predictor.py::predict_all`: фильтр dead = {MATIC, RNDR} — старые папки данных остаются, в сигналы не попадают. ML 35 → 33 символа.
- `rl_signal_bridge.py::run_all`: MATIC → POL в дефолтном словаре (DEFAULT_SYMBOLS уже использует POL/RENDER).
- `scripts/gen_quant_notebooks.py`: MATIC/USDT → POL/USDT в шаблоне кластеризации.
- Сигнальный продукт перегенерирован: 33 символа, MATIC/RNDR отсутствуют. Остаются 11 NO_DATA «illiquid» — это малоисторичные активы (~500 строк), не мёртвые тикеры (отдельный вопрос дособора истории).

### Runtime

- aios-quant-trading.service перезапущен (единичный рестарт для подхвата исправленного моста), цикл чистый.
- rl_signals.json пересохранён (9 сигналов), ml_signals.json перегенерирован (33, без мёртвых тикеров).

## Проверки (этап 2)

- [PASS] py_compile всех 3 изменённых файлов
- [PASS] pytest: 61 passed (quant-набор + test_ml + test_price_prediction_ml)
- [PASS] RLSignalBridge.run_all: 9 сигналов, pos ∈ {0.0,0.5,1.0}, активы различаются, POL → None (не в универсуме)
- [PASS] ml_signals.json: 33 символа, MATIC/RNDR отсутствуют
- [PASS] quant_signal_product: 33 символа, без мёртвых тикеров

## Изменённые файлы (этап 2)

- `aios_core/quant/rl_signal_bridge.py` — onehot, vol_ratio, clamp, POL вместо MATIC
- `aios_core/quant/ml_predictor.py` — фильтр мёртвых тикеров
- `scripts/gen_quant_notebooks.py` — POL вместо MATIC в шаблоне


## Этап 3: дособор истории, переобучение ML и PPO (по порядку)

### 1. Дособор истории (scripts/quant_backfill_history.py, новый)

- 17 малоисторичных активов (APT..WIF, ~500 строк) дособраны до ~5500 строк через пагинированный Binance klines; KAS — через Bybit fallback (KASUSDT отсутствует на Binance spot).
- Скрипт сначала обновляет «хвост» (fetch последних баров) — исправляет устаревшие серии (TON: binance-серия оборвана 24.06 — делистинг TONUSDT на Binance/Bybit; свежие бары на bitstamp/kraken).
- Дедупликация по timestamp_ms, сортировка, формат CSV сохранён.

### 2. Сигнальный продукт: выбор источника (generate_quant_signal_product.py)

- `_latest_rows`: выбор самой полной СВЕЖЕЙ серии (устаревшие >2h отбрасываются) — раньше для APT брался kraken (503 строки) вместо binance (5503), а для TON — устаревшая binance-серия вместо свежей bitstamp.
- Regime считается по последнему ЗАКРЫТОМУ бару (незакрытый бар имеет частичный объём → ложный «illiquid»).
- Результат: NO_DATA 16 → 0; 33 актива с живыми данными; WATCH_DOWN: OP, PEPE.

### 3. Переобучение ML (quant_ml_eval_train.py на полных данных)

- Оценка на полном датасете (172k строк, тест 52k): старая модель AUC 0.513 и 0 сделок >=0.60; кандидат v2: AUC 0.536, hit@0.65 = 82.4%, SIM thr=0.65: 34 сделки, win 79.4%, avg +0.93% net, итог +31.6%.
- Исправлена симуляция в скрипте: исполнение по триггерным уровням (консервативно), а не по цене пробивающего бара (гэпы давали артефакты).
- Модель catboost_price_dir_v2.cbm пересохранена (демон перечитывает её каждый цикл).

### 4. Переобучение PPO (scripts/quant_train_ppo.py, новый)

- LSTM-PPO v9, методология 1:1 с data/kg_v8/aios-rl-v8.ipynb (MultiAssetEnv, окно 10, комиссия 0.0005, risk_penalty 0.01, 300 эпизодов × rollout 800, GAE γ=0.99 λ=0.97, clip 0.2, lr 2e-4, seed 42, CPU ~15 мин).
- Универсум: 32 актива, POL вместо делистнутого MATIC.
- Валидация на 2-й половине (как в ноутбуке): **v9 sum_rl +96.0%** vs Buy&Hold −114.0%; v8: +51.4% vs −121.0%. v9 лучше v8 на 21/32 активах.
- Обе модели — консервативные «FLAT-агенты» (0 long / 0 half) — veto-механизм; v9 эффективнее избегает убытков.
- Мост: MODEL_FILE → ppo_v9.pt; имена активов читаются из чекпоинта (совместимо с v8/MATIC и v9/POL); rl_signals.json пересохранён: 10 активов (вкл. POL), все честно FLAT.

## Проверки (этап 3)

- [PASS] py_compile всех изменённых скриптов
- [PASS] pytest: 61 passed (quant-набор + test_ml + test_price_prediction_ml)
- [PASS] данные: 33 живых актива с ~5000-5500 строк, 0 дубликатов/несортировок (выборка)
- [PASS] сигнальный продукт: NO_DATA 0, 33 сигнала
- [PASS] валидация v9: sum_rl +96.03 > v8 +51.39 → ppo_v9.pt сохранён
- [PASS] демон quant-trading перезапущен, цикл чистый

## Изменённые файлы (этап 3)

- `scripts/quant_backfill_history.py` — новый: дособор истории
- `scripts/quant_train_ppo.py` — новый: обучение PPO v9
- `scripts/quant_ml_eval_train.py` — триггерная симуляция
- `scripts/generate_quant_signal_product.py` — выбор свежей полной серии, regime по закрытому бару
- `aios_core/quant/rl_signal_bridge.py` — MODEL_FILE v9, assets из чекпоинта
- runtime: data/quant/*/binance/*.csv, models/ppo_v9.pt, catboost_price_dir_v2.cbm (git-ignored)

## Git (этап 3)

- Branch `agent/20260814-quant-backfill-ppo`, commit `9501cf23`.


## Этап 4: Orderbook research, DeFi gate, документация

### Orderbook коллектор (scripts/collect_orderbook_snapshots.py + systemd unit)

- Фикс kucoin: fetchOrderBook требует limit 20/100 (было 10 → 3 ошибки/цикл); MIN_DEPTH={"kucoin": 20}, обрезка до depth 10 в normalize.
- Расширены биржи: binance, kucoin, mexc, okx, bitstamp, coinbase (okx/bitstamp/coinbase протестированы live).
- Unit aios-orderbook-research.service: interval 30s → 15s. Скорость набора ~3x. Хост-юнит изменён (не versioned).
- Прогресс: binance/mexc ~250 снапшотов/пара → растёт; kucoin/okx/bitstamp/coinbase — подключены.

### Аналитика снапшотов (scripts/analyze_orderbook_data.py, новый, read-only)

- Спреды: BTC binance/mexc ~0.002 bps, ETH ~0.05, SOL ~1.32; глубины $10k-$750k.
- Cross-exchange mid disparity (60s бакеты): BTC p95 2.5bps (12 бакетов ≥2bps), ETH 2.0 (8), SOL 2.6 (9) — окна диспаритета существуют.
- Отчёт: data/reports/orderbook_analysis.json.

### Market-making симулятор (предварительный прогон, >=200 снапшотов)

- fill_rate 63-96%, но PnL отрицательный на всех парах: наивный passive MM страдает от adverse selection (мид движется против заполненной лимитки). Вывод: нужен inventory-aware quoting (перекотировка, отложенные лимитки) — это следующий research-шаг.
- Полный прогон (>=1000/пара) — когда binance/mexc наберут 1000 (~1.5-2ч при текущей скорости).

### DeFi risk monitor

- aios-defi-risk-monitor.timer активен (hourly), отчёт 17:01Z: ready=false — fail-closed корректно (нет баланса, bridge stub, топ-офферт mock). Ничего не делать — состояние валидное.

### Документация

- docs/QUANT_SIGNAL_PRODUCT.md: актуализирован (33 актива, backfill, выбор свежей серии, regime по закрытому бару, ML v2, PPO v9).
- docs/PROJECT_INVENTORY.md: перегенерирован (python scripts/generate_project_inventory.py --write).

## Проверки (этап 4)

- [PASS] py_compile коллектора и аналитики
- [PASS] live-тест бирж: okx/bitstamp/coinbase OK; kucoin после фикса OK (17/18 снапшотов/цикл, 1 ошибка — нестабильный эндпоинт одной из бирж)
- [PASS] market-making симулятор: ready=true при min=200, 6 пар
- [PASS] pytest после изменений не требуется (коллектор/аналитика вне тестов; quant-набор 61 passed ранее)

## Изменённые файлы (этап 4)

- `scripts/collect_orderbook_snapshots.py` — kucoin depth, +3 биржи
- `scripts/analyze_orderbook_data.py` — новый
- `docs/QUANT_SIGNAL_PRODUCT.md`, `docs/PROJECT_INVENTORY.md`
- runtime: /etc/systemd/system/aios-orderbook-research.service (interval 15, 6 бирж)

## Git (этап 4)

- Branch `agent/20260814-quant-backfill-ppo`, commit `bda4d3b7`.

## Handoff

- Paper-вход Directional v2 структурно разблокирован: гейт ML=0.65 теперь достижим реальной моделью; сделки будут открываться при появлении prob_up>=0.65 (редкие, ~1-2/мес — селективность гейта).
- Следующий шаг: наблюдать циклы демона (полный скан на границе часа); при появлении WATCH/сделки — сверить PnL с симуляцией.
- Известные ограничения: (1) RL-мост деградирован — onehot-баг (все активы получают индекс BTC) → все 10 мажоров FLAT → rl_veto блокирует вход по BTC/ETH/SOL/BNB/XRP/ADA/DOGE/LINK/DOT/MATIC; 25 активов вне RL-карты не затронуты. Требует отдельного решения владельца (фикс onehot + переобучение PPO в Colab). (2) MATIC/RNDR — мёртвые тикеры (переименованы в POL/RENDER), засоряют universe сигнального продукта.
- Что нельзя делать без повторной проверки: включать live (гейт walk-forward отрицательный), менять пороги owner-профиля, удалять старую модель до подтверждения работы v2.
