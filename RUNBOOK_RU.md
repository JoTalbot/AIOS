# AIOS RUNBOOK — эксплуатация и восстановление

> Обновлено 2026-08-02. Документ описывает текущую продуктивную конфигурацию:
> LLM-балансер v2.3, автокодер v3.1 (diff-правки v3.3), трёхслойная защита от
> самоповреждения (self-protection + selfguard).

---

## 1. Карта системы

### Хост-сервисы (systemd)

| Сервис | Тип | Состояние | Назначение |
|---|---|---|---|
| `aios-auto-coder-v3.service` | loop 60s | **active** | Автономный оркестратор правок кода (TG-отчёты) |
| `aios-selfguard.service` | loop 120s | **active** | Сторож критичных файлов (снапшоты + автовосстановление) |
| `aios-telegram-bot.service` | daemon | **active** | Чат-бот (LLM через балансер) |
| `ollama.service` | daemon | **active** | Локальная LLM (последний fallback) |
| `aios-olx-collector.service` | daemon | active | Коллектор OLX |
| `aios-alertmanager-webhook.service` | daemon | active | TG-вебхук алертов |
| `aios-health-alert.service` + `.timer` | oneshot 5m | active | Health/TLS-проверки, TG-алерты при смене состояния |
| `aios-auto-promote.service` + `.timer` | oneshot 1m | active | Промоушен авто-изменений в main |
| `aios-local-backup.service` + `.timer` | daily 03:30 | active | Локальный бэкап + верификация |

### Отключено 2026-08-02 (сломано/устарело, не включать без разбора)

| Юнит | Причина |
|---|---|
| `aios-auto-coder.service` (v1) | файл унитария переименован в `.disabled.20260802`; ссылался на несуществующий `/opt/aios/.venv/bin/python3.11`, crashloop ×1303; заменён v3 |
| `aios-exporter.service` | сломан (`NameError: sys`), при этом дублирует docker-aios-exporter, который реально скрапит Prometheus |

### Docker (docker-compose.prod.yml)

| Контейнер | Порт | Примечание |
|---|---|---|
| `aios-api` | 127.0.0.1:8000 | REST + чат-эндпоинт; `LOCAL_LLM=1`, `LOCAL_LLM_BASE_URL=http://172.18.0.1:11434` |
| `aios-mcp` | 8471 | MCP-шина |
| `aios-dashboard` | 8080 | Web UI |
| `aios-exporter` | 9101 (внутр.) | Метрики → Prometheus (target 172.18.0.9) |
| `aios-prometheus` | 9090 | Метрики |
| `aios-grafana` | 3000 | Дашборды |
| `aios-alertmanager` | — | Алерты через webhook |
| `aios-autopilot` | — | Автопилот |

### Сетевые особенности
- `ufw` deny incoming; открыт 22/tcp. Порт 11434 (Ollama) разрешён **только** из docker-подсетей 172.17/172.18.
- Ollama слушает `0.0.0.0` (env `OLLAMA_HOST` в юните) — снаружи закрыта ufw.
- `/app/data` в контейнерах — named volume `aios-data`, перекрывает bind-mount `./data` (ключи `.llm_keys.json` обновлять через `docker cp`).

---

## 2. LLM-балансер v2.3 (`aios_core/llm_balancer.py`)

Единая точка доступа к LLM для всего: автокодер, чат-бот, aios-api.

### Источники ключей (по убыванию приоритета чтения)
1. `/etc/aios/*.env` (EnvironmentFile systemd-юнитов)
2. `/root/AIOS/.env` (читается при импорте модуля)
3. `/root/AIOS/data/.llm_keys.json` (в контейнерах: `/app/data/.llm_keys.json` в volume)

### Механика ротации
- Ключи внутри провайдера: least-recently-used + наименьшее число ошибок.
- 402/403 → ключ «мёртв» 24ч (×3 → permanent в рамках процесса); 429 → экспоненциальный backoff до 600с; 401 → 600с; 5xx → 60с.
- Порядок провайдеров по типу задачи: `task_type=chat|code|analysis|general` (groq/cerebras/github/mistral → … → openrouter → **local**).
- **v2.3 маппинг моделей**: если модель не из списка провайдера, подставляется его родная `models[0]` (groq-имя `llama-3.3-70b-versatile` больше не уходит на mistral); openrouter без `/` в имени → `meta-llama/llama-3.3-70b-instruct:free`.
- **LOCAL FALLBACK (v2.2)**: если ВСЕ облака недоступны → `_try_local_fallback()`: `aios-coder:7b` → `qwen2.5-coder:7b` → `qwen2.5-coder:1.5b`. Включается `LOCAL_LLM=1` (на хосте без флага — авто-включение при живой Ollama; в docker — только явно).

### Статус ключей (проверка 2026-08-02)
| Живые | Мёртвые |
|---|---|
| groq 4/4, mistral 3/3, zai 3/4, openrouter 4/5, airforce 2/3, cohere 3/3 | deepseek (402), aimlapi (403), cerebras (bad key), ibm (cfg), huggingface (402/mес), openai (нет кредитов), gemini (429 квота), openrouter#1, zai#4 |

GitHub Models — сервис закрывается GitHub (retirement brownout), не интегрирован.

### Проверка и диагностика
```bash
cd /root/AIOS
/opt/aios/.venv/bin/python scripts/check_llm_keys.py    # реальная проверка всех ключей
/opt/aios/.venv/bin/python scripts/test_balancer_e2e.py # e2e: clouds-dead→local, cohere, ротация
```
Лог ротации автокодера: `tail -f logs/coder_v3.log`.

### Добавить ключ
Файл `/root/AIOS/data/.llm_keys.json` (список на провайдера) или `*_API_KEY_N` в `/etc/aios/aios-auto-coder.env`, затем:
`systemctl restart aios-auto-coder-v3 aios-telegram-bot && docker compose -f docker-compose.prod.yml up -d aios-api && docker cp data/.llm_keys.json aios-api:/app/data/.llm_keys.json`

---

## 3. Автокодер v3.1 (`run_coder_orchestrator_v3_1.py`)

### Цикл (каждые 60s)
```
RAG-индексация → anti-loop → phase_analyze (health 0-10, issues) → phase_plan (файл+инструкция)
→ SELF-PROTECT (защищённые файлы пропускаются, в историю пишется protected_skip)
→ run_task: генерация → apply → phase_validate → phase_commit → TG-отчёт → backlog history
```

### Генерация правок (v3.3, `aios_core/autocoder_v3.py`)
- **Существующий файл → diff-режим**: LLM возвращает `<<<<<<< SEARCH / ======= / >>>>>>> REPLACE` блоки (получает до 15000 символов текущего файла). Матчинг: точный → rstrip → blank-insensitive. Сбой блока = полный отказ.
- **Новый файл → полный текст** (как раньше).
- Результат любого режима проходит `check_code_health` в `apply_fix`.
- Провайдеры генерации: `best_from_memory → groq → mistral → zai → openrouter → cohere → airforce`.
- PR: `AutoPRCreator` создаёт ветку `auto/v3/<file>-<ts>` + PR (нужен GITHUB_API_KEY с push). `AIOS_AUTO_PUSH=false` блокирует только push текущей ветки, не PR-ветки.

### Anti-loop
История `data/…backlog` (последние 50): файл 2× подряд со статусом `nothing_to_commit|skipped|blocked_validation|protected_skip` → бан в цикле; 3× за 5 → бан; дубль задачи → `[DEDUP] skip`.

---

## 4. Защита от самоповреждения (3 слоя)

### Слой 1 — `aios_core/self_protection.py`
- `PROTECTED_PATTERNS`: оркестраторы `run_coder_orchestrator*`, `run_telegram_bot.py`, `aios_core/{autocoder_v3*,llm_balancer,self_protection,code_rag,autocoder_memory,orchestrator,__init__}`, `scripts/selfguard.py`, `.env*`, `data/.llm_keys.json`, `docker-compose*.yml`, `octopus_core/api_v2_batch.py`, `aios_core/{advanced_security,inter_swarm}.py`.
- `check_code_health()`: syntax, AST-детектор заглушек (pass/... / NotImplementedError), схлопывание размера >50% (файлы >30 строк), исчезновение ≥60% функций/классов, `eval/exec/os.system`.

### Слой 2 — enforcement в пайплайне
- `AutocoderV3.apply_fix`: отказ для protected + нездорового кода.
- `run_once`: план на protected-файл → скип + `protected_skip` в историю.
- `phase_validate` (`run_coder_orchestrator.py`): protected-файл vs git HEAD + **import-smoke** `import aios_core`; при деградации — `git checkout -- <file>` и блок коммита.

### Слой 3 — `scripts/selfguard.py` (aios-selfguard.service)
- Каждые 120s проверяет 10 WATCH-файлов; здоровье → снапшот в `backups/selfguard/`; повреждение → **восстановление из снапшота + TG-алерт**.
- Загружает защиту напрямую из файла (работает при сломанном `aios_core/__init__`).
- Ручное: `selfguard.py --once`, `selfguard.py --force-snapshot`.

> ⚠️ **После намеренного большого рефакторинга WATCH-файла вручную — сразу**:
> `/opt/aios/.venv/bin/python scripts/selfguard.py --force-snapshot`, иначе сторож
> откатит вашу правку к старому снапшоту.

---

## 5. Инциденты 2026-08-02 (уроки)

1. `044b03a0`: оркестратор переписан в заглушку 166→67 строк, сервис падал каждые 10с → восстановлен, внедрена защита слои 1-2.
2. `c87c3bd4`: `aios_core/orchestrator.py` сжат до 14 строк, оборван `import aios_core` → import-smoke в phase_validate.
3. Поэтапное поедание `api_v2_batch.py` (756→80), `advanced_security.py` (329→87), `inter_swarm.py` (171→70) за ~20 автоциклов → восстановлено из origin/main, файлы в PROTECTED, адресно устранена причина (diff-правки v3.3 вместо полной перезаписи).
4. `97685f5b`: массовое удаление 170 «junk»-инструментов зацепило `tools/aios_health_alert.py` → восстановлен из git.
5. `.env`-ключи: 402/403/429 у большинства облачных провайдеров → local fallback v2.2 + маппинг моделей v2.3.

**Вывод**: полная перезапись файлов по LLM-генерации была главным вектором самоповреждения; теперь — точечные блоки + независимый сторож.

---

## 6. Типовые операции

### Логи
```bash
tail -f logs/coder_v3.log          # циклы автокодера
tail -f logs/selfguard.log         # сторож
journalctl -u aios-telegram-bot -f # чат
```

### Перезапуск после правок кода
```bash
systemctl restart aios-auto-coder-v3 aios-selfguard aios-telegram-bot
docker compose -f docker-compose.prod.yml up -d aios-api
/opt/aios/.venv/bin/python scripts/selfguard.py --force-snapshot   # если правили защищённые файлы
```

### Откат файла к последнему коммиту
`git checkout -- <file>` — selfguard также восстановит из своего снапшота в течение 2 мин.

### Полный откат к здоровому состоянию проекта
`git log --oneline -20` → найти точку до инцидента → `git checkout <sha> -- <path>` → коммит → `git push origin HEAD:main` (автопромоушен подхватит).

### Бэкапы
Ежедневно 03:30 (`aios-local-backup.timer`) + `backups/selfguard/` (критичные файлы, по 120s).

### Тесты защиты и балансера
```bash
/opt/aios/.venv/bin/python scripts/test_selfguard_e2e.py
/opt/aios/.venv/bin/python scripts/test_balancer_e2e.py
```

---

## 7. Производительность local fallback

Сервер: 4 CPU, 7.6GB RAM, без GPU. `aios-coder:7b` (Q4_K_M) занимает ~5.3GB RAM,
генерация ~1-3 мин на большой промпт автокодера; для чата короткие ответы 20-60с.
Это аварийный режим — при рабочих облаках (groq/mistral/zai) локалка не используется
(последняя в приоритете). При ограниченной памяти сменить порядок fallback на 1.5b можно
в `PROVIDERS["local"]["models"]` + `--force-snapshot`.

## Обновление v3.5 (02.08.2026, план из RESEARCH_AUTOCODERS_RU.md)

**Гейты качества (п.2/6/8):**
- `scripts/pytest_gate.py <file>` — таргетные тесты файла + сравнение с чистым HEAD
  в git-worktree; блокирует только НОВЫЕ падения; встроен в phase_validate.
  Тюнинг: `AIOS_PYTEST_GATE_TIMEOUT` (240с).
- Бюджет цикла в LLMClient: `AIOS_CYCLE_MAX_LLM_CALLS` (60), `AIOS_CYCLE_MAX_SECONDS`
  (900) — BudgetExceeded обрывает цикл до генерации (экономия ключей при 429).
- CI: `.github/workflows/auto-gate.yml` — protected-gate (`scripts/ci_protected_gate.py`),
  compile-gate, no-secrets-gate для PR в main; bypass для ops — `[ops]` в заголовке PR.

**Контекст (п.3/7):** `aios_core/repomap.py` (AST-карта 744 модулей в промпт
планировщика, кэш `data/.repomap.json`); `_window_file` в autocoder_v3 (файлы >15К —
outline + топ-5 релевантных функций); `AIOS_PLANNER_MODEL`/`AIOS_CODER_MODEL` —
оверрайд моделей фаз.

**Знания (п.4/5/9):** 420 SKILL.md по стандарту agentskills.io (`scripts/skill_lint.py`);
`skills/coder/` — боевые уроки; тела скиллов подмешиваются в генерацию
(`skill_bodies_for`); Context7-доки в планировщике; `scripts/sync_gh_issues.py`
+ `aios-gh-issues.timer` (04:15, метка `auto-coder`); `scripts/memory_to_skills.py`
+ `aios-memory-skills.timer` (пн 04:00) — кластеры ошибок → auto-lesson-скиллы.

Тесты: `scripts/test_agents_md.py`, `test_batch_b.py`, `test_batch_c.py`.

## Обновление v3.6 + balancer v2.4 (02.08.2026, второй заход: анти-цикл, ключи, бэклог)

**Анти-цикл автокодера (v3.6):** корень 12×/45мин цикла по одному файлу — правило
«задача из бэклога» било фильтр свежих файлов. phase_plan отсекает задачи, чей файл
был в последних 8 циклах истории (правило 0.1 в промпте). `nothing_to_commit` не
считается падением: PR-creator коммитит сам, поэтому при `pr.ok` в историю пишется
`success` (была ложная петля неудач по чистому дереву).

**Балансер v2.4 — provider account cooldown:** `Provider.account_cooldown_until` —
когда последний ключ провайдера уходит в 429-cooldown, провайдер пропускается 240с
(groq: 4 ключа = 1 аккаунт; раньше ~16 лишних HTTP-запросов за цикл).

**is_protected v3.6:** basename-сравнение с обеих сторон — дубль protected-файла
внутри пакета тоже блокируется; `__init__.py` защищён везде (намеренный over-block).

**Галлюцинации автокодера при мерже (устранено системно):**
- `get_logger` из logging_config → легальный алиас `get_logger = logging.getLogger`
  в `aios_core/logging_config.py` (паттерн возвращался 3 раза в разных ветках).
- `BaseSettings` из pydantic (v2: pydantic-settings) → ветки скипаются.
- `class Config` + extra=forbid → 32 ValidationError из чужих .env-переменных →
  везде `SettingsConfigDict(extra="ignore")`.
- `max_rsa_key_size` отсутствовало в trust_manager → добавлено (default 4096);
  поймано новыми `tests/test_security_trust_manager.py` (21 тест).

**Чистка ключей (02.08):** удалено 15 мёртвых: openai×3 (no credits), deepseek×3 (402),
huggingface×3 (402), aimlapi×3 (403), zai#4 (no permission), openrouter#1 (402), cerebras.
Бэкап: `backups/key_cleanup_20260802/` + копии в /etc/aios. Живые: groq 4/4 (1 аккаунт —
429-штормы), mistral 3/3, cohere 3/3, zai 3/4, openrouter 3/4, airforce 2/3; gemini×3
на месячной квоте (429), ibm (400, конфиг). .env-значения однажды засветились в
pydantic-трейсбеке (только traceback) — при паранойе ротировать TG-токен + 1 groq-ключ.

**Бэклог:** `scripts/backlog_dedup.py` + `aios-backlog-dedup.timer` (пн 04:30).
Дедуп: difflib>0.72 по описаниям, Jaccard≥0.5 по словам, фильтр protected/meta-задач.
Кап `AIOS_BACKLOG_CAP=25`, архив `data/backlog_archive*.json`. История: 131→10 ручной
чисткой (3 прохода), первый прогон скрипта 45→22.

**Таймеры (первые автозапуски — пн 03.08):** memory-skills 04:00, gh-issues 04:15,
backlog-dedup 04:30 (все OnCalendar=Mon).

Тесты: `scripts/test_balancer_acct_cd.py`, `tests/test_security_trust_manager.py`,
`tests/test_security_policy.py` (29 тестов).

## Пакеты мержа auto-веток (journal)

| # | Дата | Веток | main | Итог |
|---|------|-------|------|------|
| 2–7 | 02.08 | ~40 | `93082ef5 → ff4072a7` | feature-ветки v3.x; отброшены: 2 rollback-ветки (−2151 строк), gutting main-1323 (−37/+1), main-1236 (await вне async в octopus_core/main.py), 2× дубль runner |
| 8 | 02.08 | 2 | `ff4072a7 → b1e45419` | security_policy: pydantic-v2 валидаторы + аудит-логирование (+29 новых тестов); external_integration: рефакторинг get_integration_metrics (существующие 8/8) |

Правило пакетов: `systemctl stop aios-auto-coder-v3.service` ДО любых git-операций
(цикл 60с сгребает незакоммиченное в auto-ветки — 3 гонки зафиксированы), после —
py_compile + import-smoke изменённых МОДУЛЕЙ (не просто aios_core) + таргетные тесты,
push, `--force-snapshot`, старт сервиса.

**Security-аудит secrets (02.08, заход 3):** `scripts/secrets_scan_repo.py` — полный
скан репо на hard-coded ключи (regex-набор из SecurityPolicy + фильтр плейсхолдеров,
маски в отчёте, exit 1 при находках). Отчёт: `data/security_secrets_scan_YYYYMMDD.md`
(data/ в gitignore). Первый прогон: 4931 файл, 14 находок → 2 реальные:
1) TG-токен в `deploy/alertmanager/tg_webhook.py` (живой alerting!) → переведён на
   env `AIOS_TELEGRAM_TOKEN`, drop-in `aios-alertmanager-webhook.service.d/10-env.conf`.
   ИНЦИДЕНТ: ExecStart юнита указывал на `/opt/aios/.venv/bin/python3.11`, удалённый
   при пересборке venv (сейчас python3.12) — сервис жил «на удалённом inode» до первого
   рестарта. Урок: всегда сверять ExecStart с `ls .venv/bin/` после смены venv.
2) Дубль TG-токена + RCE (shell=True за веб-эндпоинтом) в мёртвых файлах
   `octopus_core/gemini_hack.py`, `octopus_core/gemini_tg_hack.py` → удалены (0 ссылок,
   0 процессов, 0 юнитов). git-история всё ещё содержит токены → ротация через
   @BotFather остаётся на пользователе. .env не трекается (`*.env` в gitignore).

**Ревью-пакет «security-theater» (02.08, заход 3):** 4 auto-ветки ОТКЛОНЕНЫ после
ручного диффа: active_inference-1409 (`import Authenticator` — несуществующий класс,
кирпичит модуль), web_adapter-1410 (extra=forbid на схеме запросов + html.escape всех
входящих тел + падение на X-XSS-Protection:0 — ломает живой API, sanitize_html реально
вызывается на строках 186/233), privacy_vault_v3-1413 (мандатный env-ключ в __init__ +
замена masked→encrypted ломает контракт), security_policy-1400 (regex поверх html.escape,
задача уже закрыта мержом 1351 + 29 тестами). Правила закреплены в
`skills/coder/security-hardening-review-rules/SKILL.md` (подмешивается в промпт
генерации — прицел на снижение класса «security theater»). Гонка со sweep-циклом:
незакоммиченные scanner/gemini-deleting унесло в auto-ветки — файлы восстановлены,
дисциплина «stop service перед git» обязательна (нарушена 1 раз сегодня).

---

## Android-стек и vision (обновлено 2026-08-05)

### Телефон и шлюз
- Устройство G1 (Android 15) ходит по WireGuard `10.203.0.2:<port>`; **порт adb-over-tcp
  меняется** при переподключении (на дату записи — 35075; актуальный: `adb devices` /
  `data/android_gateway/device.json`).
- Перерегистрация: `adb connect <ip:port>` → `python run_android_gateway.py register <ip:port> "G1 Android phone"`;
  watchdog и phone-brain подхватывают `device.json` сами.
- Companion: HTTP `http://10.203.0.2:8765` (токен в `data/android_gateway/companion.json`).
  Companion **не отдаёт resource-id** — в skill-селекторах надёжны только desc/text.
- Офлайн телефона: `aios-phone-inventory.timer` шлёт TG-алерт по переходу онлайн/офлайн;
  `aios-android-notifications` пропускает цикл без падения (exit 0). Поднять телефон
  с сервера нельзя — только руками на устройстве (рестарт Companion).

### vision (VLM-локатор для heal-восстановления селекторов)
Цепочка (побеждает первый живой): gemini (квота) → **mistral pixtral-12b-2409**
(основной; json_mode, temp 0) → openrouter (кредиты исчерпаны) →
**локальный Ollama qwen2.5vl:3b** (последний рубеж, полная автономия).
- `qwen2.5vl:7b` не живёт в RAM 7.6G (вытеснение/OOM) — модель на диске; после
  апгрейда VPS включается через `data/android_gateway/phone_brain_config.json`
  (`vision.ollama_model`).
- Локальная VLM: холодный старт ~2 мин, тёплый вызов 4–13 с, grounding слабее
  облаков — только страховка.

### phone-skills
- `fresh: true` на шаге app.open = force-stop перед стартом (приложение не
  продолжает открытую сессию/чат).
- Проверены на устройстве: ime_open_chat, whatsapp_open_chat, olx_open_chats
  (вкладка «Чат» в текущем UI). send_draft вживую не гоняются — реальная отправка,
  только явное подтверждение владельца.
- Планировщик не предлагает скиллы неустановленных приложений.
