# Архитектура OpenHands-контура AIOS

## Разделение ответственности

```
Human / HTTP API
   │
ContourService          ← входная точка, каноническая Task + TaskExtras, персистентность
   │
OHOrchestrator (runner) ← lifecycle: маршруты стадий, retry, finalize (git+PR)
   │
   ├── OpenHandsClient   → Cloud API v1 (разговоры ролей в sandbox)
   ├── GitHubHelper      → ветки, коммиты, diff, draft PR
   ├── state machine     → допустимые переходы, гейты, лимит retry
   ├── permissions       → check_paths против protected/deny (self_protection)
   └── OHAuditLogger     → события в канонический AuditLogger (маскирование)
```

AIOS владеет оркестрацией, состоянием, правами и аудитом; OpenHands Cloud —
исполнением. Разговоры ролей изолированы (self-contained промпты), контур
склеивает их через состояние задачи и артефакты.

## Роли (`models.AgentRole`)

MVP (`MVP_ROLES`): `orchestrator`, `architect`, `coder`, `tester`, `reviewer`.
Подключены профилями: `security`, `qa`. Задекларированы (профили F-миром позже):
`devops`, `android`, `ml`, `research`, `documentation`.

Каждая роль — `AgentProfile` в `permissions.PROFILES`: RBAC-имя, read/write,
`allowed_paths` (glob-список записи). Роль не пишет за пределами профиля —
проверка `check_paths` исполняется в finalize перед PR.

## Ключевые сущности

| Сущность | Файл | Назначение |
|---|---|---|
| `TaskExtras` | `models.py` | Контурные дополнения к `orchestrator.Task`: ветка, гейты, retry, conversation_ids, артефакты |
| `Gate` | `models.py` | Обязательные проверки: `tests`, `review`, `security_review`, `qa` |
| `FailureReport` | `models.py` | Итог финального провала: reason, attempts, files, next step |
| `ContourTask` | `service.py` | Связка `Task` + `TaskExtras` + `RunResult` |
| `RunResult` | `runner.py` | Итог прогона: status, extras, report, pr_url |

## Связь с существующим AIOS

- Каноническая `orchestrator.Task`/`TaskStatus` — не изменены (protected);
  контур использует их как носитель и проецирует свой статус
  (`COMPLETED/CANCELLED/FAILED`, остальное → `RUNNING`).
- Права — поверх `aios_core.self_protection` (protected/deny списки).
- Аудит — поверх `aios_core.audit_logger` (маскирование секретов).
- Реестр агентов — octopus `agent_orchestrator_api` (поля role/permissions/
  allowed_paths добавлены в F4); контурный оркестратор может регистрироваться
  там как агент. HTTP-монтирование контура — в host-приложение отдельным решением.

## Автопилот

`scripts/openhands_autopilot.py` — генератор задач по всему проекту: коллекторы
`ruff` и `todo` (TODO/FIXME по файлам) → очередь → `submit_queue` в `ContourService`.
Самостоятельные коллекторы добавлять в `collect_queue`; новый доменный гейт —
смотреть `docs/TASK_LIFECYCLE.md` (автоподбор `infer_gates`).

## Конфигурация

Все внешние связи — env-переменные (см. таблицу в `docs/OPENHANDS_INTEGRATION.md`).
Секреты не в коде и не в state-файле.
