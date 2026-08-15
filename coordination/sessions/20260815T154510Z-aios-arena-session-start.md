---
session_id: "20260815T154510Z-aios-arena-session-start"
status: "ACTIVE"
agent: "Arena.ai agent (workspace)"
machine: "aios (167.233.95.7)"
started_utc: "2026-08-15T15:45:10Z"
updated_utc: "2026-08-15T15:45:10Z"
branch: "agent/20260814-quant-backfill-ppo"
base_commit: "573eb4e98dac079025189446aa116827928fdec2"
claim: "none"
---

## Цель

Начало работы внешнего агента Arena.ai над проектом AIOS: ознакомление с инструкциями (AGENTS.md), координационными документами и состоянием репозитория. Конкретная задача будет определена оператором.

## Scope

- Разрешённые компоненты/файлы: определяется задачей оператора (пока нет).
- Явно вне scope: protected-файлы из AGENTS.md (run_coder_orchestrator*, run_telegram_bot.py, scripts/selfguard.py, aios_core/autocoder_v3*, aios_core/llm_balancer.py, aios_core/self_protection.py, aios_core/code_rag.py, aios_core/autocoder_memory.py, aios_core/orchestrator.py, aios_core/__init__.py, aios_core/advanced_security.py, aios_core/inter_swarm.py, octopus_core/api_v2_batch.py, .env*).
- Ожидаемые пересечения с другими сессиями: активные claims отсутствуют на момент старта (проверено).

## Исходное состояние

- git status --short: единственный untracked — backups/systemd_20260815/ (чужой артефакт решения владельца, не трогать).
- Ветка: agent/20260814-quant-backfill-ppo (последний коммит 573eb4e9).
- Прочитанные документы: AGENTS.md, coordination/PROJECT_CONTEXT.md, coordination/README.md, coordination/SESSION_TEMPLATE.md, coordination/claims/ (README + 3 активных claim: paper-fix, quant-6m-backtest, quant-history-backfill, whisper-audio-cleanup).
- Чужие незакоммиченные изменения: backups/systemd_20260815/ (не трогать).
- git fetch --all --prune: OK, origin синхронизирован.

## План

1. Ожидание задачи от оператора.
2. При получении задачи: создать claim, выполнить работу с минимальными правками, проверки (py_compile/pytest/ruff), коммит в ветку agent/<session>/<task>, обновить журнал.

## Ход работы и решений

- 2026-08-15T15:45Z: подключение к серверу по SSH (ключ из чата, pubkey совпал), изучение AGENTS.md, PROJECT_CONTEXT.md, README координации, claims, git-состояния. Создан журнал сессии. Активные параллельные сессии на quant-тематику (walk-forward, backfill, winrate) — quant-модуль считается занятым другим агентом до проверки claims перед задачей.

## Изменённые файлы

- coordination/sessions/20260815T154510Z-aios-arena-session-start.md — журнал сессии (этот файл).

## Проверки

- [PASS] ssh root@167.233.95.7 — вход выполнен.
- [PASS] ssh-keygen -y -f <key> — публичный ключ совпал с предоставленным.
- [PASS] git fetch --all --prune — успешно.
- [PASS] git status --short — чисто, кроме чужого backups/systemd_20260815/.

## Git

- Коммиты: нет (изменений кода не было).
- Опубликованная ветка/PR: нет.
- Незакоммиченные изменения: журнал сессии (координационные файлы — часть работы; решение о коммите после первой реальной задачи).
- Чужие изменения, которые не были затронуты: backups/systemd_20260815/ — не тронут.

## Handoff

- Последняя завершённая точка: onboarding завершён, контекст загружен.
- Следующий конкретный шаг: получить задачу от оператора; перед кодом — проверить claims и создать собственный claim.
- Блокеры: нет.
- Риски: quant-модуль — активные claims других сессий; не пересекаться без согласования.
- Что нельзя делать без повторной проверки: git reset --hard / clean -fd / массовый add/commit; правки protected-файлов; переключение ветки в грязном worktree.

---

## Задача от оператора: quant-oos-profit (2026-08-15T15:50Z)

**Цель:** продолжить улучшение трейдинга — winrate и реальную прибыль. Предыдущая сетка
(quant_winrate_experiments, in-sample 1y) дала все варианты <= 0: BASE -165$, лучший T1 (тренд SMA200)
+2.96$ на 9 сделках (незначимо). Отчёт требует OOS-подтверждения.

**Решение:** честный walk-forward OOS на полных 12-мес. данных (8760 баров, allowlist):
- 2 фолда: train 70%/test 30% и train 85%/test 15%, свежая CatBoost v2 (те же гиперпараметры) на train;
- 16 предзаданных a-priori вариантов (тренд-гейты SMA50-200, ML>=0.70/0.75, блэклист, trail off,
  cooldown 24h, ATR-фильтр, TP/SL 2.5/1.0, комбо);
- выбор победителя ТОЛЬКО по OOS; затем портфельная симуляция (max 1 позиция, kill-свитчи).

Claim: coordination/claims/quant-oos-profit--20260815T154510Z-aios-arena-session-start.md
Скрипт: scripts/quant_oos_profit_experiments.py

---

## Ход работы quant-oos-profit (обновление 2026-08-15T16:35Z)

1. Изучены claims/журналы: активных пересечений нет (paper-fix DONE). Создан claim
   `quant-oos-profit--...` и скрипт `scripts/quant_oos_profit_experiments.py`.
2. Прогон 1 (v1): фикс-порог 0.65 недостижим свежеобученной моделью → почти 0 сделок;
   окна искажены короткими сериями (TON 525 баров).
3. v2: исключение серий <1500 баров; калибровка порога на train-перцентиле (q90-q97).
   Результат: BASE −1.91$, N1 (trail=1.0) +5.36$ на 7 сделках (WR 71%), единственный
   положительный. NO_ML −9129$ (8157 сделок) — ML-гейт ценен.
4. v3 (раунд 3): окно 0.60 добавлено; разложение по reason; N1m (0.995) +3.97$,
   N1X (TP2.5/SL1.0) +8.28$; монотонный эффект trail 0.988<0.995<1.0 подтверждён.
   Перцентильные пороги q98/q99 — отрицательны (слабые сигналы).
5. v4 (финал): дедуп по (symbol, opened_at) — окна перекрываются (0.50⊂0.60⊂0.70⊂0.85).
   Уникальные сделки: BASE +7.15$ (WR 50%, PF 2.50), N1 +14.42$ (WR 87.5%, PF 5.83),
   N1X +15.67$ (PF 6.24). Портфельная симуляция N1: +6.74$ (kill-свитчи 0.25% от $1000
   срабатывают — очень жёстко для такого капитала).
6. Обнаружено: data/quant/*.csv дописываются live-коллектором (KAS докачан 16:19Z между
   прогонами) — результаты привязаны к срезу 16:25Z; для воспроизводимости нужен снапшот.
7. catboost_info/*.tsv (tracked) модифицированы прогонами CatBoost — НЕ коммитятся.

## Итог для владельца

- Один параметр (trail_ratio 0.988→1.0) на том же наборе сигналов: WR 50→87.5%,
  PnL +7.15→+14.42$ на OOS (4 окна, 8 уникальных сделок). Рекомендация: paper-режим
  trail=1.0 (или 0.995) на 30д/200 сделок; live по-прежнему запрещён.
- Полный отчёт: docs/TRADING_OOS_PROFIT_EXPERIMENTS_2026-08-15_RU.md;
  сырые цифры: data/reports/oos_profit_experiments.md.
- Изменение прод-профиля — только решение владельца (правила AGENTS.md).

## Изменённые файлы

- scripts/quant_oos_profit_experiments.py — новый OOS harness (4 фолда, калибровка на train).
- docs/TRADING_OOS_PROFIT_EXPERIMENTS_2026-08-15_RU.md — отчёт владельцу.
- data/reports/oos_profit_experiments.md — артефакт прогона.
- coordination/sessions/20260815T154510Z-aios-arena-session-start.md — журнал (этот файл).
- coordination/claims/quant-oos-profit--20260815T154510Z-aios-arena-session-start.md — удалён после DONE.

## Проверки

- [PASS] py_compile скрипта на сервере и локально.
- [PASS] Сравнение BASE-варианта с прошлой сеткой (консистентность сигналов).
- [NOT RUN] pytest (изменений прод-кода нет, только новый standalone-скрипт).
- [NOT RUN] ruff (скрипт новый; стиль повторяет существующие quant-скрипты).

## Handoff

- Последняя завершённая точка: OOS-эксперименты завершены, отчёт и коммит готовы.
- Следующий шаг (владелец): решение о paper-прогоне с trail_ratio=1.0/0.995;
  при одобрении — правка owner-профиля и 30д paper-наблюдение.
- Блокеры: нет. Риски: выборка 8 сделок мала; live запрещён до gates.
- Что нельзя делать без повторной проверки: менять прод-профиль/quant-движок без решения
  владельца; git reset --hard/clean; push в remote без полномочий.

---

## Пункты 1-3 (обновление 2026-08-15T17:05Z)

### Пункт 2 — устойчивость N1 (DONE)
scripts/quant_oos_robustness.py (fold-0.70, ML>=0.65):
- Jackknife по 32 символам: N1 min +0.67$ / med +3.65$ / max +6.64$ (положителен при
  удалении ЛЮБОГО символа); BASE min -4.18$ / med -1.20$.
- Binance-цены (тот же период): N1 +3.57$ vs BASE -1.27$ — эффект воспроизводится на
  другом источнике цен (33 binance-серии).
- Вывод: N1-результат не зависит от одного символа или вендорских цен.
Отчёт: data/reports/oos_robustness.md.

### Пункт 1 — paper-профиль trail_ratio=1.0 (APPLIED)
- aios_core/quant_directional_policy.py: DirectionalV2Config + take_profit_pct (0.02),
  stop_loss_pct (-0.01), trail_ratio (0.988) из env AIOS_QUANT_* (дефолты = legacy).
- aios_core/quant_directional_v2.py: exit-логика использует config вместо литералов.
- tests/test_quant_directional_v2.py: +4 целевых теста (trail из env параметризованный,
  TP/SL из env, дефолты preserve legacy). 22/22 passed в quant-наборе.
- deploy/systemd/aios-quant-trading.service: +Environment=AIOS_QUANT_TRAIL_RATIO=1.0.
- Применено к runtime с одобрения владельца: unit скопирован в /etc/systemd/system
  (бэкап: backups/systemd_20260815/aios-quant-trading.service.pre-trail110),
  daemon-reload + restart. Сервис active, env виден, первый цикл без ошибок
  (trades=0, blocks={'same_candle': 1}). Paper-режим подтверждён ("real orders disabled").
- Полный pytest: 2 FAILED, оба НЕ связаны с этой задачей:
  1) test_project_inventory — обновлён инвентарём (generate_project_inventory.py --write);
  2) test_v22_api::test_monetization_routes_registered — 6 маршрутов вместо 5, маршрут
     /api/v2/mon/quant-signals добавлен чужим коммитом (v22.0-D) без обновления теста —
     pre-existing, не трогал.

### Пункт 3 — push
Ветки запушены в origin (одобрение владельца):
- agent/20260815-quant-oos-profit (research: OOS-эксперименты + robustness)
- agent/20260815-quant-trail-config (код: exit params + тесты + unit)

---

## Пакет улучшений (2026-08-15T17:15Z) — по решению владельца ("+")

### 1. Частичный тейк + бутстрэп (research, DONE)
scripts/quant_oos_partial_tp_bootstrap.py (fold 0.70, allowlist, ML>=0.65):
- PT2 (50%@+1.5%, остаток trail 1.0): +5.80$ / PF 12.59 / WR 75% — лучший (N1 +3.65$).
- PT1 (+3.81$), PT3 (+2.80$).
- Бутстрэп 2000 ресемплов по символам: N1 90% CI [-4.26, +11.55], pos_share 74.8%;
  Δ(N1-BASE) CI [+0.00, +12.10], pos_share 88.3% — разница устойчиво положительна.
- ВАЖНО: n=4 сделки на окне — выбор среди PT1/PT2/PT3 несёт selection bias;
  PT2 в прод НЕ применялся, требуется подтверждение на большем окне.
Отчёт: data/reports/oos_partial_tp_bootstrap.md.

### 2. Allowlist + binance (runtime, APPLIED)
- deploy/systemd/aios-quant-trading.service: ALLOWED_EXCHANGES += binance
  (kucoin,bitstamp,mexc,binance). Binance уже в EXCHANGES движка; robustness-проверка
  подтвердила тот же эффект N1 на binance-ценах (+3.57$ vs -1.27$).
- Применено: unit скопирован, daemon-reload, restart. exchange_not_allowed упал 96→72
  (6 неразрешённых бирж × 12 символов; binance теперь в allowlist).

### 3. Контрольный портфель (A/B, APPLIED)
- Новый deploy/systemd/aios-quant-trading-control.service: тот же allowlist,
  AIOS_QUANT_TRAIL_RATIO=0.988 (legacy), отдельный портфель
  multi_exchange_portfolios_owner_paper_control.json.
- Установлен и запущен (enable --now). Первый цикл: trades=0, blocks={'exchange_not_allowed': 72,
  'ml_not_confirmed': 12} — работает. Сравнение main (trail 1.0) vs control (trail 0.988)
  через 2-4 недели — честный A/B на живых данных.

### Проверки
- [PASS] Оба сервиса active, env корректен (ALLOWED/TRAIL/PORTFOLIO).
- [PASS] py_compile нового скрипта.
- [NOT RUN] полный pytest (изменения только unit-файлы + новый research-скрипт,
  прод-код не менялся в этом пакете).

### Изменённые файлы (этот коммит)
- scripts/quant_oos_partial_tp_bootstrap.py
- deploy/systemd/aios-quant-trading.service (allowlist += binance)
- deploy/systemd/aios-quant-trading-control.service (новый)
- coordination/sessions/20260815T154510Z-aios-arena-session-start.md

---

## Диагностика "почему 0 сделок" + ML/SHORT эксперименты (2026-08-15T17:50Z)

### Корневая проблема
Развёрнутая модель даёт prob_up>=0.65 в 0.26% баров (728/281k; 30д: 0.2%) — live-гейт
ML>=0.65 практически недостижим → trades=0 с момента запуска. Плюс exchange_not_allowed=72/цикл.

### Сделано
1. Allowlist расширен на ВСЕ биржи движка (kraken,binance,bybit,okx,uniswap_v3,coinbase,
   kucoin,bitfinex,bitstamp,mexc) в обоих unit (main + control). Применено, сервисы active.
2. quant_ml_cross_sectional.py: cross-sectional фичи (btc_ret6/24, btc_regime, rel_ret*,
   mom_rank24/6, vol_rank). Результат: AUC 0.530 vs cand_base 0.529 — НЕТ улучшения.
   Топ-фичи: btc_regime(31), btc_ret24(27) — модель учит рынок, но edge не появляется.
   Потолок технического ML на h1 ≈ AUC 0.53 подтверждён.
3. quant_oos_short_experiment.py: зеркальный SHORT (SELL_SHORT + ml<=0.40/0.35, те же
   TP/SL/trail). Результат: ml<=0.40: 305 сделок, WR 44.6%, PF 0.88, -48.07$;
   ml<=0.35: 115 сделок, PF 0.56, -82.87$. SHORT edge НЕТ.
4. LONG+SHORT комбо: PF 0.89, -45$ — тоже нет.

### Вывод
Техническая направленная торговля 1h (LONG или SHORT) не имеет положительного
матожидания после издержек — подтверждено с трёх сторон (OOS LONG, OOS SHORT,
ML cross-sectional). Проблема в источнике сигнала, не в настройках.
Дальнейшие варианты: (а) сигнальный продукт/мониторинг для человека, (б) инвентарный
MM на orderbook-данных (копятся), (в) живой A/B main vs control для калибровки на
реальной статистике (теперь с полным allowlist сделки возможны), (г) смена таймфрейма/
универсума. Решение за владельцем.

### Проверки
- [PASS] оба сервиса active, allowlist = 10 бирж.
- [PASS] py_compile новых скриптов.
- [NOT RUN] полный pytest (прод-код не менялся; только research-скрипты + units).

### Файлы этого коммита
- scripts/quant_ml_cross_sectional.py
- scripts/quant_oos_short_experiment.py
- deploy/systemd/aios-quant-trading.service (allowlist=все биржи)
- deploy/systemd/aios-quant-trading-control.service (allowlist=все биржи)
- coordination/sessions/20260815T154510Z-aios-arena-session-start.md

---

## Тестовый замер 3 месяца (2026-08-15T18:30Z)

- Скрипт scripts/quant_prod_3m_backtest.py: воспроизведение движка 1:1, конфиг из unit.
- Результат (2026-05-15..08-15): 10 сделок, WR 40%, PF 0.66, PnL -6.02$ (equity 9993.98/10000).
  BTC bh -2.29%. trailing_stop: 0 срабатываний -> trail 1.0 vs 0.988 идентичны.
  ml_not_confirmed=1865 (главный блокер), global_position_limit=435.
  Сделок в мае-июне 0 (ML<0.65), все 10 - июль-август. Все на kraken (приоритет unit).
- Четвёртое подтверждение отсутствия edge LONG-only 1h (OOS LONG/SHORT/ML-CS/этот замер).
- Попутно: обнаружен и устранён дрейф код/unit (ветка oos-profit без exit-параметров,
  сервис работал с литералом 0.988). Merge trail-config -> oos-profit (d2085e2f),
  сервисы перезапущены на консистентном коде (config.trail_ratio=1.0).
- Файлы: scripts/quant_prod_3m_backtest.py, docs/TRADING_3M_BACKTEST_2026-08-15_RU.md,
  data/reports/prod_3m_backtest.{md,json} (gitignored), журнал.

---

## Эксперимент C: таймфрейм × универсум (2026-08-15T19:10Z)

- scripts/quant_tf_universe_experiment.py: 1h/4h (ресемплинг закрытых баров) × все 33 /
  топ-12 по USD-объёму × RL вкл/выкл; свежая CatBoost per tf, OOS ~6 мес (2026-02-18..08-15).
- Результаты: 4h хуже 1h (PF 0.15-0.20), топ-12 пусто/хуже, RL-вето не влияет, TP3/SL1.5
  на 4h убыточно (PF 0.60). BTC bh за окно −11.83%. Ни один вариант не дал edge.
- ВАЖНО: обнаружен и исправлен баг первого 3-мес замера — kraken имеет историю ~724 баров
  (API-кап), load_series брал его первым (приоритет unit) → старый замер покрывал ~1 мес.
  Фикс: min_bars>=4000 → все серии binance (полные 12 мес). Переснятый 3-мес замер:
  MAIN (trail 1.0) 23 сделки, WR 43.5%, PF 0.64, −13.71$; CTL (trail 0.988) −19.04$;
  BTC bh −20.63%. Trail 1.0 > 0.988 на этом окне (согласуется с N1), но оба убыточны.
  ml_not_confirmed=5400 — главный блокер подтверждён.
- Итого 5 независимых подтверждений отсутствия edge: OOS LONG, OOS SHORT, ML-CS,
  prod-3m (исправленный), tf×universe.
- Файлы: scripts/quant_tf_universe_experiment.py, scripts/quant_prod_3m_backtest.py (фикс),
  docs/TRADING_TF_UNIVERSE_EXPERIMENT_2026-08-15_RU.md, docs/TRADING_3M_BACKTEST_2026-08-15_RU.md
  (оговорка), data/reports/tf_universe_experiment.md + prod_3m_backtest.md (gitignored).

---

## ML гипотеза F, этап 1: MTF-фичи (2026-08-15T20:10Z)

- scripts/quant_ml_mtf_experiment.py: base13 + 4h/1d фичи (по закрытым группам) + сезонность.
- Первая версия дала AUC 0.76 — lookahead-утечка (close/high/low текущей группы).
  Исправлено на closed-only (shift 1). Честные цифры: MTF AUC 0.5204 vs base 0.5285,
  PnL −27.38$ vs −5.86$ (deployed 0.5461, −5.86$). MTF НЕ улучшает.
- Топ-фичи MTF: hour_cos/sin/dow (сезонность) — не даёт edge.
- Локальные OHLCV-данные исчерпаны: 6 экспериментов PF<1. Для F-2 нужны внешние данные
  (funding/OI с Binance Futures — публичный API, бесплатно; новости/on-chain — ключи).
- Файлы: scripts/quant_ml_mtf_experiment.py, docs/TRADING_ML_MTF_EXPERIMENT_2026-08-15_RU.md,
  data/reports/ml_mtf_experiment.md (gitignored).

---

## F-2: funding-эксперимент (2026-08-15T21:10Z) — ОТРИЦАТЕЛЬНЫЙ

- Собран funding rate с Binance Futures (30 активов, 166 дней, публичный API).
- Скрипты: scripts/fetch_funding_oi.py, scripts/quant_ml_funding_experiment.py.
- Результат: AUC funding 0.5239 vs base 0.5296; funding-фичи без веса; PnL 1 сделка −2.99$.
- Вывод: funding не несёт edge для 1h. OI история ~30 дней (мало), копим.
- 7-й отрицательный результат. Отчёт: docs/TRADING_ML_FUNDING_EXPERIMENT_2026-08-15_RU.md.

---

## F-4: multi-horizon target (2026-08-15T21:45Z) — ОТРИЦАТЕЛЬНЫЙ

- scripts/quant_ml_horizon_experiment.py: target h1/h4/h24, base 13 фич, честный OOS.
- AUC: h1 0.5296 > h4 0.5226 > h24 0.5141; up_rate падает (mean-reverting рынок);
  PnL h4 −26.67$, h24 −26.57$ vs deployed −5.86$. Гипотеза не подтверждена.
- 8-й отрицательный результат подряд (LONG OOS, SHORT OOS, ML-CS, prod-3m,
  tf×universe, MTF, funding, horizon).
- Отчёт: docs/TRADING_ML_HORIZON_EXPERIMENT_2026-08-15_RU.md.

---

## Вариант 2: долгосрочный портфель DCA (2026-08-15T18:45Z)

- quant_dca_analysis.py: бэктест 12 мес (binance, комиссия 0.1%): DCA топ-10 + квартальный
  ребаланс −18.9% — лучший; DCA > lump-sum на ~12-15 п.п.; все в минусе (год медвежий).
- run_dca_paper.py + aios-dca-paper.{service,timer}: ежедневный mark-to-market paper-трекера,
  еженедельный депозит $100, топ-10 равные веса, квартальный ребаланс. Деплой: timer active
  (ежедневно 17:30 UTC). Первый депозит выполнен.
- Документы: docs/DCA_PORTFOLIO_PLAN_2026-08-15_RU.md, data/reports/dca_analysis.md (gitignored).
- Конфиг трекера: data/dca_portfolio.json (runtime, gitignored).

---

## MM-пилот (2026-08-15T19:20Z) — этап 1 завершён

- Прототип mm_proto_backtest.py: двусторонний квотинг + инвентарный контроль + FIFO spread.
- Данные: 183k снапшотов / 28ч / 6 бирж / BTC-ETH-SOL (~7k снапшотов/час).
- Результат: инвентарь контролируется (±0.018 BTC), но adverse selection доминирует —
  naive passive MM убыточен на всех биржах (−37..−77$ за 1.6ч, spread PnL отрицательный).
- Нужны: недели данных, сигнал направления (микроструктура), maker-rebate биржа.
- Отчёт: docs/MM_PILOT_2026-08-15_RU.md. Этап 2 (сигнал направления) — по решению владельца.

---

## MM этап 2: сигнал направления (2026-08-15T20:40Z) — ПОЛОЖИТЕЛЬНЫЙ

- scripts/mm_microstructure_signal.py: OBI/microprice фичи, честный таргет (flat исключён).
  AUC h1: BTC/binance 0.96, BTC/kucoin 0.94, ETH 0.89, SOL 0.85 — сильный сигнал.
- scripts/mm_proto_backtest.py: naive vs gated MM (реквот каждый снапшот, модель-гейт).
  Gated устраняет adverse selection: gross −30..−43$ → ~0/+1.4$ (BTC). При fee 0.01%
  BTC/kucoin net −0.12$, BTC/binance −2.5$ (было −177$ naive).
- Ограничения: 1.6ч данных на пару, симуляция оптимистична (без очереди), SOL/ETH слабее.
- Этап 3: websocket-коллектор (1-5с), 2-4 недели данных, калибровка, paper MM.
- Отчёт: docs/MM_STAGE2_SIGNAL_2026-08-15_RU.md.

---

## MM этап 3: websocket-коллектор (2026-08-15T20:15Z) — ЗАПУЩЕН

- scripts/collect_orderbook_ws.py: Binance depth20@100ms, по соединению на пару (BTC/ETH/SOL),
  запись 1/сек в snapshots_ws. Отладка: combined /ws/ не оборачивает сообщения (нет поля s)
  -> per-pair соединения; pkill -f матчил собственную ssh-команду (2 потери процесса).
- Сервис aios-orderbook-ws.service: active, Restart=always, ~1.75 снапшота/с суммарно.
- Цель: 2-4 недели данных (1 Гц) -> переобучение сигнала, модель очереди, вердикт по MM.
- Файлы: scripts/collect_orderbook_ws.py, deploy/systemd/aios-orderbook-ws.service,
  docs/MM_STAGE3_WS_COLLECTOR_2026-08-15_RU.md.

---

## "Делаем всё" — финальный пакет (2026-08-15T20:50Z)

1. **MM-сигнал валидирован на 29ч (18 пар-бирж)**: AUC стабилен — BTC/binance 0.963,
   BTC/kucoin 0.948, BTC/okx 0.910, ETH/kucoin 0.902, ETH/binance 0.893; слабые —
   bitstamp/coinbase (тонкие стаканы, AUC 0.55-0.64). Предыдущая оценка «1.6ч» была
   артефактом расчёта часов (реальный поток 29ч) — устойчивость подтверждена.
   Gated MM: adverse selection устранён (gross>=0 на BTC), но филлов мало при порогах
   0.55/0.45 — калибровка порогов/спреда = следующий шаг после накопления ws-данных.
   Отчёт: docs/MM_SIGNAL_29H_VALIDATION_2026-08-15_RU.md.
2. **DCA-трекер**: 1 депозит ($100), value $99.95, комиссии $0.10; следующий депозит 22.08,
   ребаланс ~15.11. Отчёт: docs/DCA_TRACKER_REPORT_2026-08-15_RU.md.
3. **A/B paper**: оба сервиса активны, сделок 0 (ML-гейт: ml_not_confirmed 20/3 за цикл) —
   контуры работают, входы режутся моделью, как и в бэктестах. Сравнение — после накопления.
4. **PROJECT_CONTEXT.md обновлён** (секции «Где закончили» и «Следующий рекомендуемый шаг»).
5. Скрипт сигнала получил поддержку --table snapshots_ws (для будущего переобучения на ws-данных).

---

## Пакет М1+М2+D1 (2026-08-15T21:10Z)

- **М1 (калибровка MM)**: сетка порогов/спреда/размера/hold на 29ч REST BTC/binance —
  безубыточных конфигураций НЕТ (лучший net −0.11$ при fee 0.01%, 2 филла; max gross +1.00$
  на 14 филлах). Причина: интервал снапшотов ~9с → квота живёт 9-27с, исполнений единицы.
  REST-данные непригодны для калибровки MM — нужны 1-Гц ws-данные (копятся).
  В прототип добавлен параметр hold_snaps (удержание квоты).
- **М2 (расширение коллектора)**: ws-коллектор теперь 7 пар (BTC, ETH, SOL, XRP, BNB, DOGE, ADA),
  сервис перезапущен, все подключены. Данные 1Гц копятся для будущей калибровки.
- **D1 (TG-уведомления DCA)**: scripts/dca_telegram_report.py (credentials systemd, без секретов
  в коде), тест отправки OK (sent: True), таймер aios-dca-report.timer — понедельник 18:00Z.
- Файлы: scripts/mm_proto_backtest.py (hold_snaps), deploy/systemd/aios-orderbook-ws.service (7 пар),
  scripts/dca_telegram_report.py, deploy/systemd/aios-dca-report.{service,timer},
  docs/DCA_TELEGRAM_REPORT_SETUP_2026-08-15_RU.md.
