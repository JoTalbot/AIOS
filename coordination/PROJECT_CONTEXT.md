# Оперативный контекст проекта AIOS

**Последняя верификация:** 2026-08-14T11:23:03Z
**Машина:** `aios`
**Рабочий каталог:** `/root/AIOS`
**Базовый commit аудита:** `356bd628` (`main`, на старте совпадал с `origin/main`)
**Каноническая версия в `VERSION`/`pyproject.toml`:** `19.9.0`

> Репозиторий изменяется с разных машин и разными ИИ-агентами, иногда параллельно. Перед любой работой обязательно прочитать `AGENTS.md`, `coordination/README.md`, этот файл, активные claims и `git status`.

## Где закончили

Завершён cost-aware walk-forward Directional v2: 35 активов, OOS average −0.354%, positive 34.3%, PF 0.374. Стратегия не проходит gate; freeze/live ban подтверждены данными. Commit: `276950cd`. Отчёт: `docs/TRADING_WALK_FORWARD_2026-08-14_RU.md`; журнал: `coordination/sessions/20260814T123000Z-aios-arena-quant-walkforward.md`.

Runtime Directional v2: active/paper, `AIOS_QUANT_ENTRY_MODE=enabled` в owner-approved constrained profile (решение 2026-08-14T12:20Z), фактических entries 0. Live запрещён. Базовая реализация: `e7d24414`, `61f70b1b`.

**Проверено 2026-08-15T11:45Z:** за 18ч непрерывной работы trades=0, entry_count=0, портфель нетронут. Доминирующая блокировка — `exchange_not_allowed`=96 на каждом полном скане: allowlist `kucoin,bitstamp,mexc` почти не пересекается с универсумом 33 активов, поэтому кандидаты отсекаются ещё до ML-гейта (`ml_not_confirmed` 4-17). Это конфигурационное сужение, а не отказ модели; расширение allowlist или сужение универсума — решение владельца.

**2026-08-14T16:15Z (paper-fix):** paper-вход структурно разблокирован без изменения owner-профиля. Деградированная ML-модель (prob_up=0.433 const, AUC 0.504, гейт 0.65 недостижим) заменена scale-free CatBoost v2 (AUC 0.533; hit@prob>=0.65 = 81-83% на двух независимых OOS-окнах; avg net +0.6-0.7%/сделка по правилам движка). Журнал: `coordination/sessions/20260814T160500Z-aios-arena-paper-fix.md`; ветка `agent/20260814-paper-fix`, commit `8d668f03`. Live запрещён. Закрыто в 16:35Z (этап 2): RL-мост исправлен (onehot по ASSET_ORDER, vol_ratio вместо vol_chg, clamp; 9 мажоров честно FLAT — модель v8 не видит входов, veto консервативен), мёртвые тикеры MATIC/RNDR исключены из ML-сигналов и RL-универсума (ML 35→33). Закрыто в 17:15Z (этап 3): история дособрана до ~5000-5500 баров по всем 33 живым активам (Binance + Bybit fallback для KAS; TON: binance-серия делистнута 24.06, используются bitstamp/kraken); ML переобучена на полных данных (AUC 0.536, hit@0.65 82.4%, SIM +31.6%); PPO v9 обучена по методологии kg_v8 на локальных данных (sum_rl +96.0% vs BH −114%; v8: +51.4%) и развёрнута (мост читает assets из чекпоинта); сигнальный продукт: NO_DATA 16→0, regime по закрытому бару, выбор самой полной свежей серии. Ветка `agent/20260814-quant-backfill-ppo`, commit `9501cf23`. Живой RL-сигнал остаётся консервативным veto (все FLAT) — входа по RL-активам нет, это by design среды. 17:45Z (этап 4): orderbook-коллектор расширен до 6 бирж (kucoin depth-фикс, okx/bitstamp/coinbase), интервал 15с — скорость набора ~3x; аналитика снапшотов + cross-exchange диспаритеты в `scripts/analyze_orderbook_data.py`; предварительный MM-прогон: naive passive MM убыточен (adverse selection), нужен inventory-aware подход; полный прогон при >=1000 снапшотов/пара (binance/mexc ~250/1000, ~1.5-2ч); DeFi gate fail-closed корректно. Ветка `agent/20260814-quant-backfill-ppo`, commit `bda4d3b7`. 21:10Z (этап 7): WATCH-верификация — WATCH_DOWN precision 59.4% (143 сигнала), WATCH_UP 0 сигналов (правило слишком строгое в медвежьем рынке); ML drift monitor (hourly timer) и автообучение ML (weekly timer, deploy-only-if-better) установлены; feature-эксперимент: расширение 13→21 фич НЕ улучшает (AUC 0.5326 vs 0.5355) — базовый набор остаётся. Ветка `agent/20260814-quant-backfill-ppo`, commit `3171c6b4`. 21:30Z (этап 8, ВАЖНО): обнаружен методологический артефакт — историческая валидация PPO v8/v9 без clamp давала «скрытые шорты» (act<-1.5 → позиция -0.5, невозможная в развёрнутой политике); исторические «прибыли» (+51/+96%) — артефакты. Честная OOS-оценка с clamp: v9 = FLAT (0.0 vs BH -233%) — ценность = избегание убытков. v10 (честный сплит 70/30) не развёрнута. ML горизонты: h1 оптимален (h4/h8/h24 хуже), модель v2 остаётся. Для RL-заработка нужен явный SHORT-экшен (решение владельца). Ветка `agent/20260814-quant-backfill-ppo`, commits `174c3951`, `db27bdb4`.

Предыдущие этапы: test hermeticity `201df1eb`, tracking policy `b75c7c14`, dependency contract `7bd3e1e7`, deployment source `2be18e3a`, version consistency `c4a788cc`.

## Текущий архитектурный срез

AIOS — production-монорепозиторий, объединяющий:

- ядро оркестрации, конституционные политики, память, RAG/ChromaDB и LLM-балансер (`aios_core/`);
- автокодер и self-protection/selfguard;
- FastAPI/Starlette API, MCP, CLI, dashboards и Telegram/desktop-интерфейсы;
- интеграции OLX/social/messenger/Android/phone;
- финансовые, trading, freelance и revenue-пайплайны;
- Octopus-модули и крупную библиотеку skills;
- systemd- и Docker-production-контуры, мониторинг и CI/CD.

На момент аудита:

- 5 879 отслеживаемых файлов, 547 328 строк, 22.1 MiB;
- 3 344 Python-файла / 338 405 строк Python;
- AST-разбор всех отслеживаемых Python-файлов: 0 синтаксических ошибок;
- 36 активных `aios-*` systemd-сервисов, 54 таймера, 13 Docker-контейнеров;
- 0 failed systemd-сервисов AIOS;
- production venv использует Python 3.12.13, проект декларирует `>=3.11`.

## Приоритет продукта

Согласно `ROADMAP_NEXT.md`, главный приоритет — v20 «Activation»: перевод уже созданных возможностей в измеримый безопасный production/revenue-контур. Новые каркасные модули без работающего runner запрещены принципом `No new skeletons`.

Фактические названия активных systemd-сервисов содержат v20/v21, но теперь явно считаются версиями отдельных rollout-контуров. Они не повышают package version автоматически. Канонический источник версии основного продукта — `VERSION`; обязательные зеркала и release checklist описаны в `docs/RELEASE_VERSION_POLICY.md`.

## Текущая параллельная работа

На момент верификации активных claims и незакоммиченных файлов нет. Последняя историческая dirty LLM proxy работа завершена в `39bec522`. Перед новой задачей всё равно проверять `coordination/claims/` и `git status`.

## Runtime operator decisions

- `2026-08-15T11:35:00Z`: `aios-groq-key.service` остановлен, disabled и masked (`/dev/null`). Причина: `ExecStart` ссылался на `groq_key_retry.py`, которого нет ни в ФС, ни в git-истории; unit был в restart-loop (7832 рестарта, ~2833/сутки). Функцию выполняет живой преемник `aios-groq-autopilot.timer` (hourly, 8 ключей, status ok). Base unit сохранён в `backups/systemd_20260815/` и в `deploy/systemd/`. Снапшот masks обновлён. Журнал: `coordination/sessions/20260815T113500Z-aios-arena-ops-fixes.md`.

- `2026-08-14T11:23:03Z`: `aios-freelance-brain.service` намеренно остановлен и отключён владельцем; состояние `inactive`, `disabled`, процессов 0. Не запускать/enable без нового решения. Журнал: `coordination/sessions/20260814-aios-arena-freelance-stop.md`.
- `2026-08-14T12:20:00Z`: `aios-quant-trading.service` active/enabled в owner-approved constrained paper profile: отдельный state, max 1 позиция, ML≥0.65, confidence≥0.88, DD/day kill 0.25%. Первый цикл entries=0; live запрещён. Orderbook, Signal Monitor и DeFi risk timers active.

## Главные риски

1. **✅ Дрейф текущей версии — mitigated:** `VERSION` каноничен, API/docs publication используют его цепочку, статические зеркала проверяются тестом, исторические v9/v16 документы помечены snapshot.
2. **✅ Deployment/systemd drift — mitigated:** canonical Compose закреплён; 159 installed unit names, drop-ins, masks и host overrides представлены; strict runtime drift 0, применение units остаётся отдельной operator-approved операцией.
3. **🟡 Крупные модули — controlled:** quant engine уменьшен до 1 898 строк; budgets блокируют рост dashboard/accounts/account-control/quant, следующий seam описан в `docs/MODULE_DECOMPOSITION_PLAN.md`. Остальные монолиты декомпозируются только по одному seam.
4. **✅ Dependency drift — mitigated:** роли minimal 12 / full direct 47 / exact lock 198 формализованы и проверяются; конфликт WebSockets/Web3 устранён, production lock воспроизводим на Python 3.11.
5. **✅ Tracking/ignore risk — mitigated:** глобальный `*.json` удалён, source build-каталог возвращён в Git, runtime/sensitive paths игнорируются точечно и проверяются тестом.
6. **✅ Устаревающие repository metrics — mitigated:** текущие цифры генерируются в `docs/PROJECT_INVENTORY.md`, CI проверяет exact snapshot; старые audit-документы помечены historical.
7. **✅ Негерметичный test baseline — mitigated:** live LLM/runtime paths заменены mocks/tmp fixtures; полный suite 5 160 = 5 153 passed, 7 skipped, 0 failed.
8. **✅ Runtime/generated artifacts — mitigated:** logs, CatBoost event и debug capture больше не tracked; физические production files сохранены и игнорируются точечно.
9. **✅ LLM proxy/Kilo unfinished work — completed:** 36-model catalog, tool routing/SSE, Colab guards и atomic sync покрыты тестами и развернуты; runtime healthy.
10. **🟡 Trading expectancy — controlled/frozen:** честный OOS walk-forward отрицательный (average −0.354%, PF 0.374); entries/live запрещены, пока новая гипотеза не пройдёт fresh OOS и 30d/200-close gates.

## Следующий рекомендуемый шаг

1. Regime v3 и arbitrage-only OOS отклонены. Arbitrage: 90 folds, 1 trade, net −$0.506, positive 0%. Freeze сохраняется; следующий рациональный путь — monitoring/signal product или отдельные high-frequency orderbook данные.
2. Не включать paper entries и live: текущий Directional v2 gate отрицательный.
3. Следующий architecture seam: `tg_bot/accounts.py` context/router + analytics handler.
4. Любое применение versioned systemd units выполняется отдельно с operator approval; массовые restart/disable/remove запрещены.

## Правило обновления этого файла

Обновлять только после значимой завершённой задачи, смены общего приоритета или подтверждённого изменения runtime. Не превращать файл в подробный лог: детали принадлежат отдельным журналам `coordination/sessions/`.
