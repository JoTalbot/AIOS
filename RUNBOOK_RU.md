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
