# AIOS Architecture Audit

> **Дата аудита:** 2026-08-25 · **Base commit:** `0cabd94` (`main`, shallow clone)
> **Версия:** `19.9.0` (`VERSION`, зеркала: `pyproject.toml`, FastAPI metadata)
> **Аудитор:** OpenHands (cloud sandbox), сессия `coordination/sessions/20260825T025700Z-openhands-sandbox-audit-integration.md`
> **Характер аудита:** read-only. Код не изменялся. Секреты (`.env*`, `data/.llm_keys.json`) не читались — зафиксирован только факт их наличия в `.gitignore`/AGENTS.md.
>
> **Легенда состояния компонентов:**
> **PROD** — подключён к docker-compose.prod.yml / systemd / run_* entrypoints;
> **ACTIVE** — импортируется production-модулями;
> **EXPERIMENTAL** — standalone, только тесты/скрипты;
> **STUB** — минимальный каркас без потребителей.

---

## 1. Current Architecture

AIOS — самомодифицирующаяся распределённая система (`3537` Python-файлов, `531` тестовый файл, ~5377 тестов). Центр — `aios_core/` (~500+ модулей), вокруг — слои:

```
run_*.py entrypoints (~80+)          ← systemd units (deploy/, ~219 файлов) + docker-compose.prod.yml
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ API-слой: aios_core/api (FastAPI, основной), main.py         │
│ (Starlette, GraphQL), octopus_core (FastAPI routers),        │
│ aios_mcp (MCP gateway :8471), api_layer/ (STUB)              │
├──────────────────────────────────────────────────────────────┤
│ Ядро: aios_core/orchestrator.py (Task/TaskStep +             │
│ Constitution check per step), planner.py, ai_planner.py,     │
│ autocoder_v3.py + run_coder_orchestrator*.py (self-coding),  │
│ llm_balancer.py (key rotation/fallback), code_rag.py         │
├──────────────────────────────────────────────────────────────┤
│ Мультиагентность: aios_core/agents/* (BaseAgent + 5 доменных │
│ агентов), agent_swarm.py, multi_agent_orchestrator.py,       │
│ octopus_core/agent_orchestrator_api.py (HTTP registry/tasks/ │
│ experience), agents/ (STUB-дерево)                           │
├──────────────────────────────────────────────────────────────┤
│ Governance: constitution/ (md), constitution_engine.py       │
│ (7-фазный pipeline), policies/*.yaml, rbac.py,               │
│ self_protection.py (PROTECTED_PATTERNS), audit_logger.py     │
├──────────────────────────────────────────────────────────────┤
│ Домены: quant/trading (quant_*, treasury, kraken), Android   │
│ RPA (android_*, phone_*), OLX/marketplace, tg_bot, swarm/*   │
└──────────────────────────────────────────────────────────────┘
Персистентность: SQLite/JSON state, ChromaDB (compose), volumes
aios-data/aios-chroma/aios-logs; координация: coordination/
```

**Ключевая особенность:** система уже содержит работающий self-coding контур
(autocoder v3 → `run_coder_orchestrator_v3_1.py` systemd-сервис, ветки `auto/v3/*`,
auto-PR, self-protection gate, pytest-gate) и «конституционное» управление —
то есть значительная часть того, что предлагается строить для OpenHands,
в AIOS уже существует в собственном виде.

---

## 2. Existing Agent System

| Компонент | Файл | Классы | Назначение | Состояние |
|---|---|---|---|---|
| Доменные агенты | `aios_core/agents/base.py`, `analytics_agent.py`, `sales_agent.py`, `support_agent.py`, `voice_agent.py`, `negotiation.py`, `workflow.py` | `BaseAgent`+`AgentState`, `AnalyticsAgent`, `SalesAgent`, `SupportAgent`, `VoiceAgent`, `NegotiationAgent`, `SalesWorkflow` | Бизнес-агенты (аналитика, продажи, поддержка, голос, переговоры). Вход: сообщения/контекст; выход: ответы/действия | **ACTIVE** — endpoints в `main.py` (`/api/v1/agents/process` L93, `/negotiate` L319, voice L335, workflow L368) |
| Мульти-оркестратор агентов | `aios_core/agents/orchestrator.py` (258 строк) | `MultiAgentOrchestrator` | Роутинг между доменными агентами | **ACTIVE** (main.py, aios_core/orchestrator.py) |
| Swarm | `aios_core/agent_swarm.py` | `AgentRole(StrEnum)`, `SwarmAgent`, `SwarmMessage`, `SwarmDecision`, `AgentSwarm` | Рой агентов с консенсусом | **ACTIVE** (main.py, dashboard, intelligence/swarm_controller.py) |
| Multi-agent orchestrator (core) | `aios_core/multi_agent_orchestrator.py` | — | Координация агентов внутри Orchestrator | **ACTIVE** |
| **Agent Registry (HTTP)** | `octopus_core/agent_orchestrator_api.py` | `AgentRegistration` (L55), `AgentStatus` (L64), endpoints `/agents/register` (L137), `/agents` (L173), `/agents/{id}/heartbeat` (L179), `/status` | Регистрация внешних агентов: agent_id, model, project, capabilities, max_parallel, priority; heartbeat; JSON-state | **ACTIVE** (router в `octopus_core/main.py` L217-218) |
| Experience pool (shared memory агентов) | там же, `/experience/share` (L454), `/experience/search` | `ExperienceShare` (L85) | Обмен опытом между агентами | **ACTIVE** |
| Корневое дерево | `agents/agent_registry.py` (+8 файлов, 2–8 строк) | `AgentRegistry` и др. | Каркас «registry foundation» | **STUB** — потребителей нет; дублирует концепцию octopus-registry |
| Swarm-дополнения | `aios_core/role_coordinator.py`, `aios_core/inter_swarm.py` | — | Межроевая координация | **EXPERIMENTAL** |

**Вывод:** реально работающий Agent Registry уже существует — это
`octopus_core/agent_orchestrator_api.py` (HTTP, JSON-state, capabilities, heartbeat).
Создавать второй registry не нужно — расширять этот.

---

## 3. Existing Planner

| Компонент | Файл | Что делает | Состояние |
|---|---|---|---|
| Planner | `aios_core/planner.py` | Инстанцируется внутри `Orchestrator` — разбиение задач на шаги | **ACTIVE** |
| AI-планировщик | `aios_core/ai_planner.py` (128 строк) | `AITaskPlanner.decompose_goal` (L44), `self_correct_plan` (L88) через `LLMRouter` | **ACTIVE** (но LLMRouter — mock-path, см. §8) |
| Автокодер-пайплайн | `run_coder_orchestrator.py` (1466 строк, shared library) | Фазы: `phase_analyze` L326 → `phase_plan` L499 → `phase_code` L779 → `phase_validate` L930 → `phase_commit` L1059 → `build_report` L1128; backlog `pending → in_progress`; цикл-статусы: `success/error/skipped/failed/passed/nothing_to_commit/protected_skip/blocked_validation` | **PROD** (через v3_1 runner) |
| Task scheduler | `aios_core/task_scheduler.py` (293 строки) | `TaskPriority`, `TaskScheduleStatus`, `ScheduledTask`, recurring/retry/tick | **ACTIVE** (generic, мало потребителей) |
| Task graph | `aios_core/task_graph_executor.py` | `AutonomousTaskGraphExecutor` | **EXPERIMENTAL** |
| Очередь задач | `aios_core/tasks/` (`client.py`, `worker.py`, `evolution_tasks.py`) | ARQ/Redis enqueue stubs + evolution cycle | **STANDALONE** |
| Goal synthesis | `aios_core/goal_synthesizer.py`, `goal_decomposer_v2.py` (STUB) | Автономные цели | **EXPERIMENTAL/STUB** |
| Octopus tasks | `octopus_core/agent_orchestrator_api.py` `/tasks/submit` (L193), `/orchestrate` (L292) | `TaskSubmission`: batch commands, idempotency_key, dedup по fingerprint, competition_mode, priority | **ACTIVE** |

---

## 4. Existing Memory

| Компонент | Файл | Назначение | Состояние |
|---|---|---|---|
| MemoryManager | `aios_core/memory_manager.py` | Общая память (learning, reasoning, advisor, orchestrator, mcp) | **ACTIVE** |
| Autocoder memory | `aios_core/autocoder_memory.py` | Память автокодера: уроки, решения, неудачные подходы | **ACTIVE** (autocoder_v3, finetune, self_protection) |
| Code RAG | `aios_core/code_rag.py` | RAG-индекс кодовой базы для автокодера | **ACTIVE** |
| Agent memory | `aios_core/agent_memory_system.py` | Память агентов (metrics, rag_augmentation, dashboard) | **ACTIVE** |
| Experience pool | `octopus_core/agent_orchestrator_api.py` | Межагентный опыт (share/search) | **ACTIVE** |
| Coordination | `coordination/` (PROJECT_CONTEXT, sessions, claims) | Межмашинная/межагентная «рабочая память» проекта | **PROD (процесс)** |
| `memory/` package | `memory/long_term_memory.py` и др. | long/short-term + sync | **STUB/EXPERIMENTAL** |
| Graph memory | `aios_core/graph_memory.py` | — | **EXPERIMENTAL** (1 потребитель-скрипт) |

**Вывод:** создавать новую Memory-систему не нужно. Для OpenHands-интеграции
расширяются `autocoder_memory` (уроки/решения) и/или octopus experience pool.

---

## 5. Existing Constitution

| Механизм | Файл | Суть | Состояние |
|---|---|---|---|
| AGENTS.md | `AGENTS.md` (корень) | «Конституция» для ИИ-агентов: золотые правила, protected-файлы, workflow, бюджеты модулей | **PROD (процесс)** |
| Constitution docs | `constitution/ARTICLE_I_SUPREME_PRINCIPLE.md`, `core_principles.md` | 67 статей / 1320 правил (по ARCHITECTURE.md) | **ACTIVE** |
| ConstitutionEngine | `aios_core/constitution_engine.py` | 7-фазный evaluation pipeline: required fields → restricted actions → MUST NOT → YAML policies → risk → principles → ALLOW/DENY/REVIEW | **ACTIVE** (тесты; шаг `evaluate` в Orchestrator) |
| Политики | `policies/security_policy.yaml`, `evolution_policy.yaml`, `federation_policy.yaml` | Ограничения, парсятся RuntimePolicy | **ACTIVE** |
| Self-protection | `aios_core/self_protection.py` | `PROTECTED_PATTERNS` + `is_protected()` — жёсткий gate в цикле автокодера | **ACTIVE (единственный реальный enforcement)** |
| RBAC | `aios_core/rbac.py` | `Permission`, `PermissionSet`, `Role`, `RoleHierarchy`, `AccessPolicy`, `RBACEngine.check_access` (L448) | **ACTIVE-ish** (потребители — в основном тесты) |
| Audit | `aios_core/audit_logger.py` | `AuditLogger`: record/query/stats, retention 90d | **ACTIVE** |
| Governance stubs | `governance/policy_engine.py`, `rule_engine.py` | `evaluate` → auto-approve/auto-pass | **STUB** ⚠ |
| Secrets | `aios_core/secret_manager.py`, `credential_manager.py`, `local_secrets.py` | API-key store, XOR-store | **ACTIVE/EXPERIMENTAL** |
| Selfguard | `scripts/selfguard.py` | Снапшоты protected-файлов после ручных правок | **ACTIVE** |

---

## 6. Existing Tests

- **531 тестовый файл**, ~5377 `def test_*`.
- Каталоги: `tests/{chaos,e2e,integration,load,macro,performance,production,security,universal,v5,fixtures}`.
- Конфиг: `pyproject.toml [tool.pytest.ini_options]`, `asyncio_mode="strict"`; маркеры `slow`/`integration` применяются точечно; корневой `conftest.py` + `tests/conftest.py` (auto-mark asyncio).
- CI (`.github/workflows/`, 18 файлов): `ci`, `docker`, `coverage`, `core-gates`, `supply-chain`, `release(+docker)`, `docs-check`, `secrets-scanning`, `aios-validation`, `aios-v5-tests`, `deploy` (VPS compose).
- Канон локально: `pytest tests/ -q`, `ruff check .`, `python -m py_compile`, `scripts/check_module_size_budget.py --strict`, `scripts/check_dependency_contract.py --strict`.
- Android/E2E: `tests/e2e`, `conftest_android.py`, `Dockerfile.android`, Appium/ADB-мосты в `aios_core/android_*`.

---

## 7. Existing Infrastructure

- **docker-compose.prod.yml** (канонический прод): `aios-api` (run_rest_api :8000), `aios-p2p` (:8001), `aios-commercial`, `aios-mcp` (:8471), `aios-dashboard` (:8080), `aios-autopilot`, `aios-telegram-bot` (profile bot), `aios-telegram-exporter`, `prometheus`, `grafana`, `alertmanager`, alert-canary; volumes `aios-data/aios-chroma/aios-model-cache/aios-backups/aios-logs`; образ pinned по sha256 в ghcr.io/jotalbot/aios.
- **systemd:** `deploy/` (~219 units/timers), ключевой — `deploy/aios-auto-coder-v3.service` (PROD-автокодер, interval 60s, `AIOS_AUTO_COMMIT=true`, `AIOS_AUTO_PUSH=false`, `LOCAL_LLM=1`); drift-аудит: `scripts/audit_deployment_sources.py --runtime` (read-only).
- **K8s/Helm/Terraform:** `k8s/`, `helm/aios`, `terraform/` — каркасы.
- **Мониторинг:** `deploy/monitoring/` (prometheus.yml, alertmanager→TG webhook, grafana dashboards), `aios_core/observability*`, metrics exporter.
- **Прод-хост:** `/root/AIOS`, venv `/opt/aios/.venv` (см. RUNBOOK_RU.md). Данная среда аудита — облачная песочница, прод-хост недоступен и не трогался.

---

## 8. Existing Problems

| # | Проблема | Severity | Причина | Влияние | Рекомендация |
|---|---|---|---|---|---|
| P1 | `aios_core/autocoder_v3_1.py` **не существует**, но PROD-runner `run_coder_orchestrator_v3_1.py` (L47-50) пытается его импортировать и молча откатывается на `AutocoderV3` | **HIGH** | Модуль удалён/не создан; fallback маскирует рассинхрон | Прод-юнит работает «не на том» классе; документированный контракт v3.1 не выполняется | Либо создать `autocoder_v3_1.py` (наследник с заявленными отличиями), либо явно переименовать контракт и убрать fallback. Решение — за владельцем (файл в protected-контуре) |
| P2 | Фрагментация моделей задачи: 5 параллельных `Task`/`TaskStatus` (`orchestrator.py`, `task_scheduler.py`, `distributed_queue.py`, `fleet_scheduler.py`, `distributed_computing.py`) + octopus `TaskSubmission` | **HIGH** | Органический рост без единой схемы | Невозможен единый state machine / audit / retry для «задачи» | Канонизировать `aios_core/orchestrator.py::Task` как доменную модель; внешние адаптеры (octopus, scheduler) маппить на неё |
| P3 | Тройной API-слой: `aios_core/api` + `octopus_core` + `api_layer/` (STUB) + `aios_core/v5/api` | **MEDIUM** | Gateway-задум не завершён | Размазывание auth/моделей, растёт attack surface | Не расширять `api_layer/`; новые endpoints — только в существующие приложения |
| P4 | `governance/policy_engine.py` / `rule_engine.py` — auto-approve/auto-pass стабы | **MEDIUM** | Каркас без реализации | Иллюзия enforcement; реальный gate только `self_protection` в цикле кодера | Либо реализовать, либо явно пометить как non-enforcing; для OpenHands-контура использовать `self_protection` + RBAC |
| P5 | Хардкод prod-путей: `octopus_core/agent_orchestrator_api.py:39` `STATE_DIR=/root/agents/-Octopus/...` | **MEDIUM** | Путь прибит к прод-хосту | Невоспроизводимость вне прода, падение тестов вне хоста | Вынести в env (`AIOS_STATE_DIR`) с дефолтом |
| P6 | Корневое `agents/` — STUB-дерево, дублирующее концепции registry/coordinator | **LOW** | Ранний каркас | Шум, риск что агенты-ИИ начнут «использовать» пустышки | Пометить deprecated в README каталога или удалить отдельным решением владельца |
| P7 | ~500+ экспериментальных модулей (`quantum_*`, `singularity_*`, `infinite_*`) в `aios_core/` | **LOW** | Генеративный рост | Навигационный шум; реальный риск деградации при массовых правках | Соблюдать `check_module_size_budget.py`; новый код — в отдельные пакеты (`aios_core/openhands/`), не в монолиты |
| P8 | `LLMRouter` — mock-path (`_mock_generate` L78) при активных потребителях | **LOW** | Незавершённая реализация | AI-планировщик фактически детерминирован | Для OpenHands-контура LLM не нужен от AIOS — у OpenHands свой LLM-стек |
| P9 | Protected-контур без авто-теста наличия файлов: отсутствие protected-модуля (P1) не поймано CI | **MEDIUM** | selfguard снапшотит существующее | Молчаливая деградация | CI-проверка «protected files exist & import» |

---

## 9. OpenHands Integration

Факты: упоминаний OpenHands/all-hands в коде, деплое, workflows и docs **нет**
(нашлись только файлы данной coordination-сессии). `aios_core/openhands/` и `.agents/` отсутствуют.

### Что уже можно использовать (не дублировать)

| Потребность интеграции | Существующий аналог | Действие |
|---|---|---|
| Agent Registry | `octopus_core/agent_orchestrator_api.py` (register/heartbeat/capabilities/status) | **Расширить** полями `role/permissions/allowed_paths/parent_agent/current_task` |
| Task queue / submission | octopus `/tasks/submit` (idempotency, dedup, competition) | Использовать как транспорт; доменная модель — `orchestrator.Task` |
| Task модель + статусы | `aios_core/orchestrator.py::Task/TaskStatus` | **Канонизировать**, маппить статусы OpenHands-контура на неё |
| Shared agent memory | octopus experience pool + `autocoder_memory.py` | Хранить уроки/решения OpenHands-агентов там же |
| Constitution / политики | `constitution_engine` (ALLOW/DENY/REVIEW), `policies/*.yaml`, `self_protection.is_protected` | Прогонять каждое действие OpenHands-контура через evaluate + protected-gate |
| Permissions | `aios_core/rbac.py` (Role/PermissionSet/AccessPolicy) | Маппить роли агентов (Architect/Coder/…) на Role |
| Audit log | `aios_core/audit_logger.py` + `coordination/sessions+claims` | Писать события задач OpenHands-контура туда же (без секретов) |
| Git workflow | `AutoPRCreator` (autocoder_v3): ветки, PR, protected-gate | Повторить паттерн: `agent/task-<id>` ветки, PR, no direct main |
| LLM | `llm_balancer.py` | **Не использовать** для OpenHands (у OH свой LLM); оставить для AIOS-циклов |
| Контракт инженерных правил | `AGENTS.md` | Расширить секцией OpenHands (НЕ перезаписывать — см. конфликт C1 в плане) |

### Что нужно добавить

1. `aios_core/openhands/` — изолированный адаптер к OpenHands API (client/models/profiles/conversations/errors) — отсутствует полностью.
2. Контур состояний задачи интеграции (state machine) поверх `orchestrator.TaskStatus` с обязательными gates (tests/review/security).
3. Retry-policy (max_retries=3) + failure-отчёты.
4. Роли агентов (Orchestrator/Architect/Coder/Tester/Reviewer) как **профили/промпты** над OpenHands conversations + записи в octopus-registry — не как новые классы-агенты в `aios_core/agents/`.
5. `.agents/skills/aios-*` — OpenHands-совместимые скиллы (отдельно от существующего `skills/` с `index.json` — это другая система, см. конфликт C2).
6. CI-проверка protected-файлов (P9).

### Что нужно изменить (минимально)

- `octopus_core/agent_orchestrator_api.py`: поля registry + env для `STATE_DIR` (P5).
- `AGENTS.md`: добавление секции про OpenHands-контур (только с подтверждением владельца — файл является конституцией репо).
- `aios_core/orchestrator.py`: расширение `TaskStatus` недостающими статусами (REVIEW/SECURITY_REVIEW/QA/BLOCKED) — обратимо-совместимо (StrEnum, добавление значений). Файл protected → только вручную/с selfguard-снапшотом.

### Что менять НЕ нужно

- Protected-файлы (`autocoder_v3.py`, `llm_balancer.py`, `self_protection.py`, `code_rag.py`, `orchestrator.py` — ядро, `run_coder_orchestrator*`, `octopus_core/api_v2_batch.py` и пр. из PROTECTED_PATTERNS).
- Существующий self-coding контур v3 — OpenHands-контур идёт **рядом**, не заменяя.
- `docker-compose.prod.yml`, systemd units (кроме добавления нового unit для контура — отдельным решением).
- `skills/` (существующая система скиллов автокодера) — не мигрировать.
