# AIOS — репозиторный и runtime-анализ

**Дата аудита:** 2026-08-14
**Хост:** `aios`
**Каталог:** `/root/AIOS`
**Ветка и исходный commit:** `main` / `356bd628`
**Версия в `VERSION` и `pyproject.toml`:** `19.9.0`
**Тип аудита:** полный статический обход всех Git-tracked файлов + read-only проверка production runtime

> Это исторический снимок на дату аудита. Текущие автоматически проверяемые repository metrics: [`PROJECT_INVENTORY.md`](PROJECT_INVENTORY.md).

## 1. Резюме

AIOS — крупный production-монорепозиторий, в котором одновременно находятся:

- платформенное ядро оркестрации и конституционного управления;
- LLM routing, RAG, память, skills и мультиагентные механизмы;
- автокодер и защита от самоповреждения;
- API, MCP, CLI, dashboards, Telegram и desktop-интерфейсы;
- OLX/social/messenger/Android/phone интеграции;
- trading, finance, freelance и revenue-пайплайны;
- systemd, Docker, мониторинг и крупный CI/CD-контур.

Проект реально работает на production-хосте: во время аудита были активны 36 `aios-*` systemd-сервисов, 54 AIOS-таймера и 13 Docker-контейнеров; failed AIOS-сервисов не было.

Статическая база выглядит технически жизнеспособной: все 3 344 отслеживаемых Python-файла успешно разобраны AST-парсером без синтаксических ошибок. Главная проблема не в отсутствии функций, а в сложности управления быстро растущей системой: документация и версии расходятся, deployment имеет несколько источников истины, зависимости описаны тремя разными наборами, а до этого аудита не было явного межмашинного handoff-протокола.

## 2. Методика и границы

Выполнено:

1. Полный обход вывода `git ls-files` — 5 879 файлов.
2. Подсчёт строк, размеров, расширений и распределения по верхнеуровневым каталогам.
3. AST-разбор каждого tracked `*.py` без записи `__pycache__`.
4. Подсчёт классов, функций, async-функций, тестовых функций и внутренних импортов.
5. Анализ root-документации, архитектуры, roadmap, runbook, статусов и `AGENTS.md`.
6. Read-only разбор compose, workflow и systemd-файлов.
7. Read-only сверка фактических systemd/Docker/Python состояний.
8. Сравнение `pyproject.toml`, `requirements.txt` и `requirements.lock`.
9. Проверка Git-состояния и уже существующих незакоммиченных файлов.

Не выполнялось:

- чтение значений `.env`, токенов, credentials и приватных runtime-данных;
- сетевые/e2e операции, финансовые действия и отправка сообщений;
- рестарт сервисов или изменение deployment;
- полный `pytest tests/ -q` на production-хосте с чужой незавершённой работой;
- семантическое построчное code review всех 547 тысяч строк.

Поэтому «полный анализ» здесь означает полный репозиторный охват автоматизированными статическими проверками и архитектурный анализ ключевых контуров, а не доказательство корректности каждой бизнес-функции.

## 3. Фактические метрики репозитория

| Метрика | Значение |
|---|---:|
| Git-tracked файлов | 5 879 |
| Размер tracked-содержимого | 22.1 MiB |
| Всего строк | 547 328 |
| Python-файлов | 3 344 |
| Строк Python | 338 405 |
| Markdown-файлов | 1 942 |
| Классов по AST | 2 945 |
| Функций по AST | 18 989 |
| Async-функций | 1 628 |
| Test-функций по AST | 6 238 |
| Синтаксических ошибок Python | 0 |
| `tests/` Python-файлов | 480 |
| Root `run_*.py` | 113 |
| Workflow-файлов GitHub Actions | 34 |
| Tracked systemd `.service` | 36 |
| Tracked systemd `.timer` | 18 |

### Крупнейшие области по числу строк

| Область | Файлов | Строк | Назначение/наблюдение |
|---|---:|---:|---|
| `aios_core/` | 966 | 157 335 | Основное ядро; самая высокая архитектурная связность |
| `skills/` | 2 593 | 103 449 | Большая библиотека skills, включая код, тесты и документацию |
| `tests/` | 480 | 65 280 | Основной тестовый контур |
| `docs/` | 394 | 43 636 | Архитектура, конституция, отчёты, roadmap |
| root | 217 | 34 853 | 113 runners, API/bootstrap и операционные точки входа |
| `attic/` | 34 | 31 789 | Исторические копии; заметная доля объёма и риска путаницы |
| `octopus_services/` | 110 | 27 850 | Отдельные сервисы и frontend/runtime assets |
| `scripts/` | 168 | 14 145 | Операционные и сервисные скрипты |
| `tg_bot/` | 32 | 12 060 | Telegram handlers и доменная логика |

## 4. Архитектурная карта

### 4.1. Внешние интерфейсы

- `main.py` — FastAPI/NiceGUI приложение и часть REST/WebSocket surface.
- `aios_core/api/` — расширенный API-контур и mixins.
- `aios_mcp/` — MCP/JSON-RPC gateway.
- `aios_cli/`, `aios_cli.py`, `aios_cli_admin.py` — операторские CLI.
- `dashboard*`, `dashboard/`, `converge/` — dashboards и unified messenger UI.
- `run_telegram_bot.py`, `tg_bot/` — Telegram control plane.
- Signal/Viber/Chrome/VNC runners — desktop-адаптеры.

Наблюдение: интерфейсный слой исторически эволюционировал несколькими путями. Документация одновременно упоминает Starlette и FastAPI, а разные compose-файлы публикуют разные наборы сервисов/портов.

### 4.2. Оркестрация, политики и автономность

Ключевые зоны:

- `aios_core/orchestrator.py` и связанные planner/execution модули;
- constitution/policies/governance слои;
- agent architecture, swarm, debate, reflection и multi-agent orchestrator;
- evolution/self-healing/autonomy;
- `run_coder_orchestrator*.py` и autocoder v3;
- `aios_core/self_protection.py` + `scripts/selfguard.py`.

Сильная сторона — в проекте уже есть явные protected-файлы, risk/review gates и watchdog критичных исходников. Это особенно важно при параллельной работе автономных агентов.

### 4.3. LLM, память и знания

- `aios_core/llm_balancer.py` — центральный LLM routing/fallback-контур.
- RAG/code RAG/context compression/processing.
- SQLite storage, memory managers, agent memory.
- ChromaDB runtime store.
- Knowledge graph и retrieval.
- Colab farm/ingest/heartbeat и локальный Ollama fallback.

По внутренним импортам среди центральных модулей находятся `aios_core.storage`, `aios_core.llm_balancer`, `aios_core.orchestrator`, `aios_core.agent_memory_system` и API app.

### 4.4. Доменные контуры

Проект содержит много вертикалей с общей платформой:

- OLX/inventory/sales/TTN и marketplace adapters;
- Instagram/Facebook/Signal/Viber/Telegram;
- Android gateway, phone brain и mesh fleet;
- freelance, CRM и client lifecycle;
- treasury, on-chain listener, DeFi/liquidity/quant trading;
- monitoring, alerts, backups, self-healing.

Это даёт большую функциональность, но увеличивает риск скрытой связанности через общие storage, credentials, LLM balancer и Telegram control plane.

### 4.5. Skills и Octopus

`skills/` — крупнейшая область по количеству файлов. В ней 2.5 тысячи tracked-файлов и более 100 тысяч строк. Skills содержат не только Markdown, но и Python/TypeScript, references и собственные тесты. Octopus представлен отдельными core/services/ops/projects/instructions/roadmap зонами.

Рекомендация: считать skills отдельным supply-chain контуром, проверять происхождение, исполняемые разрешения, зависимости и contract tests независимо от основного API.

### 4.6. Deployment и эксплуатация

Compose-карты:

- `docker-compose.yml` — 5 сервисов;
- `docker-compose.unified.yml` — 4 сервиса;
- `docker-compose.prod.yml` — 13 сервисов.

Production compose включает API, P2P, commercial, MCP, dashboard, autopilot, Telegram, Prometheus, Grafana, Alertmanager и exporters. Критичные порты в production в основном привязаны к `127.0.0.1`, что является хорошей базовой практикой.

Фактический runtime шире tracked deployment:

- 36 активных AIOS systemd-сервисов;
- 94 загруженных `aios-*` service units;
- 54 AIOS-таймера;
- 13 Docker-контейнеров;
- 0 failed AIOS units.

Следствие: текущий хост частично является источником истины сам по себе; не все установленные units отражены в tracked `deploy/systemd/`.

## 5. Сильные стороны

1. **Живой production runtime:** сервисы и observability реально запущены.
2. **Синтаксическая целостность:** 0 AST syntax errors во всех tracked Python-файлах.
3. **Большой тестовый контур:** 480 Python-файлов только в `tests/`, 6 238 test-функций по всему репозиторию.
4. **Self-protection:** protected patterns, selfguard и правила минимальных diff.
5. **Security CI:** CodeQL, gitleaks, secret scan, supply-chain и image scanning workflows.
6. **Наблюдаемость:** Prometheus, Grafana, Alertmanager и exporters.
7. **Локальные привязки портов production compose:** уменьшена внешняя поверхность.
8. **Развитая документация:** много архитектурных и эксплуатационных материалов, даже если часть устарела.
9. **Изоляция секретов:** `.env` не отслеживается Git; есть runtime credentials tooling.
10. **Функциональная декомпозиция Telegram:** фактический `run_telegram_bot.py` уже 1 402 строки, а значительная логика вынесена в `tg_bot/`.

## 6. Проблемы и риски

### P0 — параллельная работа без явного handoff

На старте уже были три чужих незакоммиченных файла в общем worktree. До аудита корневой `AGENTS.md` не объяснял, как нескольким машинам/агентам заявлять scope и передавать незавершённый контекст.

Риск: случайный `reset`, `clean`, массовый stage или конфликтующие правки.

Принятое действие: добавлен каталог `coordination/`, журналы сессий, advisory-claims и обязательный раздел в `AGENTS.md`.

### P1 — дрейф версии

Одновременно встречаются:

- `VERSION` / `pyproject.toml`: `19.9.0`;
- `ARCHITECTURE.md`: `16.0.0`;
- `main.py` FastAPI metadata: `16.0.0`;
- `EXECUTIVE_SUMMARY.md`: `9.3.1`;
- `docs/STATUS.md`: `9.3.0`;
- активные service descriptions: v20/v21.

Риск: неверная диагностика, release labeling, API metadata и решения агентов на основании устаревшего контекста.

### P1 — несколько deployment-источников истины

Три compose-файла и установленный systemd-контур описывают разные системы. Tracked units: 36/18, runtime: 94/54.

Риск: «успешный» deploy не воспроизводит production; orphan units продолжают работать; runbook отстаёт.

### P1 — крупные и связанные модули

Крупнейшие production Python-файлы:

| Файл | Строк |
|---|---:|
| `aios_core/dashboard.py` | 3 495 |
| `tg_bot/accounts.py` | 3 226 |
| `run_account_control.py` | 2 375 |
| `aios_core/quant_trading_engine.py` | 2 157 |
| `aios_core/api/mixins_core.py` | 1 594 |
| `aios_core/agent_memory_system.py` | 1 575 |
| `run_coder_orchestrator.py` | 1 467 |
| `run_telegram_bot.py` | 1 402 |

Риск: высокая стоимость review, конфликтов и regression. Декомпозиция нужна постепенно, с compatibility tests и без массового rewrite.

### P1 — dependency drift

- `pyproject.toml`: 12 runtime dependencies;
- `requirements.txt`: 45;
- `requirements.lock`: 198.

В `requirements.txt`, но не в project metadata, находятся FastAPI, SQLAlchemy, Redis, ChromaDB, Telegram, OpenAI, Web3, Torch и другие существенные зависимости. В project metadata, но не `requirements.txt`, находятся `python-dotenv` и `requests`.

Риск: разные способы установки создают разные продукты.

### P1 — широкое игнорирование JSON

`.gitignore` содержит глобальный `*.json`, после которого точечно возвращены только отдельные JSON assets.

Риск: новый важный manifest/config/report незаметно не попадёт в Git. Это особенно опасно для автономных агентов, которые могут считать сохранённый локальный JSON частью репозитория.

### P2 — устаревшие документы и метрики

Примеры:

- `docs/STATUS.md` сообщает 162 Markdown-файла, фактически tracked Markdown — 1 942, в `docs/` — 366;
- root architecture сообщает 438 tests, AST обнаруживает 6 238 test-функций;
- roadmap всё ещё описывает `run_telegram_bot.py` как 511 KiB/8700+ строк, фактически текущий tracked файл — 1 402 строки после декомпозиции.

Риск: агенты планируют уже выполненную работу или неверно оценивают масштаб.

### P2 — runtime/generated артефакты в Git

Обнаружены отслеживаемые лог/telemetry/test-image файлы, включая `app.log`, несколько `octopus_core/*.log`, CatBoost event file и debug image в `attic`.

Риск: шум, рост истории, случайное включение чувствительных данных.

### P2 — версия Python

`AGENTS.md` говорит Python 3.11, `pyproject.toml` требует `>=3.11`, production venv использует Python 3.12.13.

Это не формальная несовместимость, но CI/runtime matrix должна явно включать фактическую production-версию.

### P2 — исторические и дублирующие зоны

`attic/` содержит более 31 тысячи строк и крупные snapshots. Есть многочисленные поколения roadmap/architecture/status документов.

Риск: поиск/RAG/агенты выбирают устаревший файл вместо канонического.

## 7. Тестирование и качество

### Результат статической проверки

- 3 344 Python-файла разобраны `ast.parse`;
- `SyntaxError`: 0;
- обнаружены отдельные `SyntaxWarning` об invalid escape sequence в Octopus/tools/skills коде — это технический долг, не блокирующая синтаксическая ошибка.

### Почему полный pytest не запускался в этой сессии

Аудит выполнялся на production-хосте, где:

- активно множество сервисов;
- в общем worktree уже есть чужие изменения;
- тестовый набор крупный и может импортировать широкую поверхность проекта.

Безопасный вариант — отдельный worktree/clone от зафиксированного commit, затем:

```bash
source /opt/aios/.venv/bin/activate
pytest tests/ -q
ruff check .
```

Результат нужно записать в отдельный session journal вместе с commit и окружением.

## 8. Git-состояние на старте

`main` совпадал с `origin/main` (`0/0`), но worktree не был чист:

```text
 M scripts/llm_balancer_openai_proxy.py
?? scripts/sync_kilo_llm_models.py
?? tests/test_llm_proxy_models.py
```

Diff изменённого proxy был существенным: +427/-113 строк. Аудит не изменял и не индексировал эти файлы. Они считаются чужой активной работой до явного handoff.

## 9. Рекомендованный план

### Немедленно

1. Применять `coordination/README.md` для каждой новой сессии.
2. Владельцу LLM proxy зарегистрировать отдельный журнал/claim и завершить свою работу path-scoped коммитом.
3. Запретить destructive Git-команды в грязном общем worktree.
4. Для параллельных агентов на одном сервере использовать отдельные worktrees/clones.

### Следующий короткий спринт

1. Создать генерируемый `SYSTEM_INVENTORY.md` или CI artifact из фактических файлов/runtime.
2. Выбрать `VERSION` единым источником; API metadata и docs получать из него.
3. Обозначить один production deployment manifest и задокументировать отношения остальных.
4. Экспортировать установленные `aios-*` units, сравнить с `deploy/systemd/`, классифицировать drift.
5. Свести dependency declaration к одному входу и воспроизводимому lock.
6. Убрать глобальный `*.json` либо документировать обязательные exceptions/tests.
7. Удалить tracked runtime logs/telemetry из будущих snapshots после проверки на чувствительные данные.

### Среднесрочно

1. Декомпозировать крупные модули по измеримым boundaries, начиная с тестируемых seams.
2. Добавить архитектурные ownership/Codeowners границы для core, bot, finance, Android, deployment и skills.
3. Помечать устаревшие roadmap/architecture документы заголовком `HISTORICAL`, чтобы RAG не считал их актуальными.
4. Добавить CI-проверки:
   - согласованность версии;
   - согласованность dependency sets;
   - наличие session/handoff для автоматических agent branches;
   - отсутствие tracked runtime logs;
   - обнаружение важных ignored JSON.
5. Выполнять регулярный полный test/lint прогон в изолированной среде, не на общем production worktree.

## 10. Итоговая оценка

AIOS обладает широкой production-функциональностью, зрелыми защитными механизмами и большим тестовым/документационным массивом. Система находится на стадии, где основная угроза — не недостаток возможностей, а несогласованность быстро меняющихся частей и параллельных изменений.

Наиболее выгодное направление — не добавление новых skeleton-модулей, а:

- единые источники истины;
- воспроизводимый deployment;
- актуальный inventory;
- управляемая декомпозиция;
- обязательный межмашинный session/handoff-протокол;
- безопасный перевод существующих функций в измеримый production/revenue-контур.

С этого аудита точка продолжения хранится в `coordination/PROJECT_CONTEXT.md`, а подробности каждой работы должны сохраняться отдельным файлом в `coordination/sessions/`.
