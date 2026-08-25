# AIOS × OpenHands — Integration Plan

> **Дата:** 2026-08-25 · **Base commit:** `0cabd94` (`main`)
> **Основание:** `AIOS_ARCHITECTURE_AUDIT.md` (тот же коммит)
> **Статус:** ПЛАН. Реализация не начата. Каждая фаза — отдельный коммит/PR с проверкой.
> **Принцип:** расширять существующее, не дублировать; protected-файлы не трогать автоматически.

---

## 0. Архитектурные конфликты master-prompt ↔ AIOS (зафиксированы, не ломаем)

| # | Конфликт | Решение |
|---|---|---|
| C1 | Master-prompt предлагает **создать `AGENTS.md`** — файл уже существует и является конституцией репозитория (золотые правила, protected-список, coordination-протокол) | **Не перезаписывать.** Правила из master-prompt (Этап 6) вливаются как новая секция существующего `AGENTS.md` отдельным малым PR, после подтверждения владельца |
| C2 | Master-prompt предлагает `.agents/skills/` — в репо уже есть `skills/` (с `index.json`, `skills/coder/*`, `skills/core/*`) — система уроков/скиллов автокодера | **Сосуществование.** `.agents/skills/aios-*` — OpenHands-стандарт (SKILL.md), читаемый OpenHands-агентами; `skills/` — внутренняя система AIOS. Не мигрировать одно в другое |
| C3 | Статусы master-prompt (`CREATED/PLANNING/READY/RUNNING/TESTING/REVIEW/SECURITY_REVIEW/QA/BLOCKED/FAILED/COMPLETED/CANCELLED`) vs существующий `orchestrator.TaskStatus` (7 значений) | **Маппинг + расширение**: добавить недостающие значения в `TaskStatus` (StrEnum — обратимо-совместимо); `CREATED`→`PENDING`, `READY`→`PLANNING`-завершён, `TESTING/REVIEW/...` — новые значения |
| C4 | Branch-имена `agent/task-001` из master-prompt vs конвенция репо (`auto/v3/<file>-<ts>`, `agent/<date>-<name>`) | Ветки контура: `agent/oh-<task_id>` — вписывается в существующий префикс `agent/` |
| C5 | Retry master-prompt (`max_retries=3`) vs существующий цикл кодера (`MAX_ERRORS=5`, cooldown) | Независимые контуры: у OpenHands-оркестратора свой счётчик 3; у автокодера v3 остаётся своё |
| C6 | Master-prompt предполагает «зелёное поле» для Orchestrator/Registry/Task system — всё это частично существует | См. §2: reuse-map. Дубликаты не создаются |

---

## 1. Целевая архитектура

```
Human / Telegram / API
        │
        ▼
┌─────────────────────────── AIOS ───────────────────────────┐
│  OH-Orchestrator (новый, aios_core/openhands/orchestrator) │
│     │                                                      │
│     ├── Task model ──────► aios_core/orchestrator.Task     │  (канон, расширенные статусы)
│     ├── Agent Registry ──► octopus_core/agent_orchestrator │  (расширенный, НЕ новый)
│     ├── Policy gate ─────► constitution_engine.evaluate    │
│     │                    + self_protection.is_protected    │
│     ├── Permissions ─────► aios_core/rbac.py               │
│     ├── Audit ───────────► aios_core/audit_logger.py       │
│     │                    + coordination/sessions           │
│     ├── Memory ──────────► autocoder_memory + experience   │
│     └── Git/PR ──────────► паттерн AutoPRCreator           │
│                            (ветки agent/oh-<id>, PR,       │
│                             main не трогаем)               │
│     │                                                      │
│     ▼                                                      │
│  OpenHands Client (aios_core/openhands/ — adapter)         │
└─────┬──────────────────────────────────────────────────────┘
      │ REST (OpenHands Cloud / agent-server API)
      ▼
OpenHands conversation(s) → sandbox → git branch → tests → diff
      │
      ▼
Tester → Reviewer → (Security) → QA → PR → human/controlled merge
```

Ключевое проектное решение: **роли агентов (Architect/Coder/Tester/Reviewer) — это
профили OpenHands-разговоров (system prompt + skills + allowed tools/paths), а не
новые Python-классы агентов.** AIOS владеет оркестрацией, состоянием, правами и аудитом;
OpenHands владеет исполнением в sandbox.

---

## 2. Reuse-map (что НЕ создаём заново)

| Блок master-prompt | Существующий механизм AIOS | Действие |
|---|---|---|
| Agent Registry | `octopus_core/agent_orchestrator_api.py` | Расширить `AgentRegistration`: `role`, `permissions` (ref на RBAC Role), `allowed_paths`, `memory_scope`, `parent_agent`, `current_task` |
| Task system | `aios_core/orchestrator.py::Task` + octopus `TaskSubmission` | `Task` — доменная модель; octopus — HTTP-транспорт; поля `tests_required/review_required/security_review_required/artifacts` — в `Task` (dataclass-расширение) |
| State machine | `TaskStatus` + lifecycle в `Orchestrator.run()` | Добавить статусы; переходы — в новом модуле контура (см. §4) |
| Constitution/Policy | `constitution_engine`, `policies/*.yaml`, `self_protection` | Gate перед RUNNING и перед COMMIT |
| Permissions | `aios_core/rbac.py` | Завести Role на каждую роль агента (§6) |
| Audit log | `audit_logger.py` + `coordination/sessions` | События задачи писать туда; секреты не логировать |
| Memory | `autocoder_memory.py` + octopus experience pool | Уроки/решения/провальные подходы |
| Git workflow | `AutoPRCreator` (ветки `auto/v3/*`, PR, return-to-main) | Тот же паттерн, префикс `agent/oh-` |
| Retry/budget | `AIOS_CYCLE_MAX_*` в run_coder_orchestrator | Аналогичные env-лимиты для контура |

---

## 3. Новый пакет (единственное новое дерево кода)

```
aios_core/openhands/
├── __init__.py          # re-exports, __all__
├── models.py            # OHTask поля-расширения, AgentProfile, роли (StrEnum)
├── state_machine.py     # допустимые переходы + gate-проверки
├── client.py            # OpenHandsClient: conversations, wait, events, errors; таймауты
├── profiles.py          # 5 MVP-профилей: system prompts, skills refs, allowed_paths
├── permissions.py       # маппинг роль → rbac.Role + enforcement allowed_paths
├── orchestrator.py      # OHOrchestrator: lifecycle задачи, retry, gates
├── audit.py             # обёртка над audit_logger (маскирование секретов)
└── github.py            # branch/commit/diff/PR helper (паттерн AutoPRCreator)
```

Ничего из перечисленного не входит в PROTECTED_PATTERNS. Зависимости — только
существующие модули + `httpx` (проверить наличие в `requirements.lock`; если нет —
через dependency contract с обоснованием).

---

## 4. State machine

```
PENDING(=CREATED) → PLANNING → READY → RUNNING → TESTING → REVIEW
      → SECURITY_REVIEW → QA → COMPLETED

Ошибки:  RUNNING→FAILED · TESTING→FAILED · REVIEW→BLOCKED
         SECURITY_REVIEW→BLOCKED · QA→FAILED
         любой → CANCELLED (ручное/политикой)

Gate-правила (hard):
- →COMPLETED запрещён, если tests_required и tests не зелёные;
- →COMPLETED запрещён, если review_required и нет APPROVED;
- затронут protected-файл → автоматический SECURITY_REVIEW/BLOCKED
  (self_protection.is_protected), правка — только вручную + selfguard snapshot;
- retry_count ≥ 3 → FAILED + TASK_FAILURE_REPORT.md (artifacts).
```

Реализация: `state_machine.py` — таблица переходов + функции-gates; статусы
добавляются в `orchestrator.TaskStatus` отдельным малым PR (файл protected —
правка вручную/владельцем + `selfguard --force-snapshot`).

---

## 5. MVP-агенты (профили, `profiles.py`)

| Роль | read | write | Инструменты/ограничения |
|---|---|---|---|
| Orchestrator | all | orchestration (tasks, reports) | Не правит код; только маршрутизация и статусы |
| Architect | all | `docs/design/**`, `*.md` планов | Без `git commit` в чужие ветки |
| Coder | project | assigned workspace (ветка `agent/oh-<id>`) | protected-файлы запрещены gate'ом |
| Tester | project | `tests/**`, `reports/**` | Не правит product-код |
| Reviewer | all | review reports | Read-only к коду; выдаёт APPROVED / CHANGES_REQUESTED |

Будущие (после зелёного MVP): Security, DevOps, Android, ML, Research, Documentation, QA —
каждый = новый профиль + запись в registry, без новых подсистем.

Reviewer — **отдельный conversation** от Coder (независимость по master-prompt).
Reviewer проверяет: соответствие задаче, архитектуру, качество, regression, тесты,
security, документацию, unnecessary complexity.

---

## 6. Permissions → RBAC

- Для каждой роли из §5 заводится `rbac.Role` с `PermissionSet` (ресурсы `repo:*`,
  `repo:tests`, `docs:design`, `reports:*` и т.д.) и `allowed_paths` (glob-список).
- Enforcement точки: (1) перед стартом conversation — фильтр prompt/скиллов;
  (2) после завершения — проверка `git diff --name-only` против `allowed_paths` и
  `self_protection.is_protected`; нарушение → BLOCKED + audit-запись.
- Секреты: профилям передаётся явный allowlist секретов (по умолчанию — пустой);
  `GITHUB_TOKEN` — только профилям, создающим PR.

---

## 7. Audit log

Событие на каждый переход: `task_id, agent, timestamp, action, input(digest),
output(digest), files_changed, tests, decision`. Писать в `audit_logger`
+ зеркало в `coordination/sessions/<session>.md`. Маскирование: фильтр по
паттернам (token/key/secret/password/cookie) до записи — `audit.py`.

---

## 8. Git workflow

```
main
 ├── agent/oh-<task_id>-<slug>   ← вся работа OpenHands
 └── auto/v3/*                    ← существующий автокодер (не пересекается)
```

Перед PR: `git diff` review → `pytest tests/ -q` (минимум затронутые) →
`ruff check` → `py_compile` изменённых → secrets-scan → protected-check →
PR (draft по умолчанию) со связью на задачу и списком тестов.
Прямые коммиты в main — запрещены gate'ом. Commit message: `oh(<role>): [task-id] desc`.

---

## 9. Фазы внедрения (один PR = одна фаза, после каждой — проверка)

| Фаза | Содержание | Проверка | Зависимости |
|---|---|---|---|
| F0 | ✅ Аудит + этот план + coordination-журнал | Документы в репо | — |
| F1 | `aios_core/openhands/` skeleton: `models.py`, `state_machine.py` + unit-тесты переходов/gates | `pytest` новых тестов; `ruff`; size-budget | — |
| F2 | `permissions.py` + RBAC-роли + `audit.py` (маскирование) + тесты | тесты; ручной прогон check_access | F1 |
| F3 | `client.py` (OpenHands API) + `profiles.py` (5 MVP) + errors/timeouts; тесты на уровне контракта (recorded responses, без моков бизнес-логики) | contract tests; auth через `OPENHANDS_API_KEY` из env | F1 |
| F4 | Расширение octopus registry (`role/permissions/allowed_paths/parent_agent/current_task`) + `STATE_DIR`→env (P5) | API-тесты router'а; обратная совместимость полей (все новые — optional) | F2 |
| F5 | `orchestrator.py` пакета: lifecycle Task через state machine, retry=3, failure report; GitHub helper (ветка/PR) | интеграционный тест на тестовой задаче в песочнице | F1–F4 |
| F6 | `TaskStatus` extension (protected, вручную/владельцем) + selfguard snapshot | полный `pytest tests/ -q` | F5 |
| F7 | `.agents/skills/aios-{architecture,testing,security,github,devops}/SKILL.md` (OpenHands-формат; НЕ трогаем `skills/`) | ручная загрузка скилла OpenHands-агентом | F0 |
| F8 | Секция OpenHands в существующий `AGENTS.md` (C1) — после подтверждения владельца | review владельца | F7 |
| F9 | First test task end-to-end (малые правка неprotected-функции): Architect→Coder→Tester→Reviewer→PR(draft) | вся цепочка зелёная; отчёт | F1–F8 |
| F10 | Документация `docs/AIOS_AGENT_ARCHITECTURE.md`, `OPENHANDS_INTEGRATION.md`, `AGENT_DEVELOPMENT.md`, `TASK_LIFECYCLE.md`, `SECURITY_MODEL.md`, `TESTING_AGENT_SYSTEM.md` — только по факту реализованного | соответствие коду | F9 |
| F11 | Test matrix (Этап 20) + финальный `OPENHANDS_IMPLEMENTATION_REPORT.md` | матрица пройдена | F9–F10 |

Protected-файлы на всех фазах: не изменяются автоматически; F6 — единственная
точка касания (вручную). CI-добавка «protected exist & import» (P9) — отдельный
малый PR внутри F1–F2.

---

## 10. Ограничения среды и открытые вопросы к владельцу

1. Данный аудит выполнен в облачной песочнице OpenHands, не на прод-хосте
   (`/root/AIOS`, `/opt/aios/.venv` недоступны). Все команды из AGENTS.md
   (`source /opt/aios/.venv/bin/activate`, systemd) применимы только на хосте.
2. **Q1:** подтвердить P1 (отсутствующий `autocoder_v3_1.py`) — создавать модуль
   или менять runner? (protected-контур, решение владельца).
3. **Q2:** подтвердить добавление секции в `AGENTS.md` (C1) и расширение `TaskStatus` (F6).
4. **Q3:** OpenHands-контур — только Cloud API (`OPENHANDS_API_KEY`) или планируется
   self-hosted agent-server рядом с прод-стеком (тогда отдельный compose-сервис)?
5. **Q4:** где живут state-файлы контура — `data/` (как octopus) подтверждается?
