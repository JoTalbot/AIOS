# OpenHands × AIOS — отчёт о реализации

## Summary

По утверждённому плану фаз F0–F11 (`AIOS_OPENHANDS_INTEGRATION_PLAN.md`) построен
**OpenHands-контур AIOS**: AIOS управляет OpenHands-агентами (оркестрация, состояние,
права, аудит), OpenHands Cloud исполняет задачи в sandbox. Реализация велась пофазно
(ветка → коммит → draft PR → подтверждение), без изменения protected-файлов,
без удаления существующего функционала.

Итог: **14 модулей** (`aios_core/openhands/`, ~1820 строк), **114 тестов контура**
(+ octopus-регресс 8), **10 draft PR** (#218–#227), полный lifecycle
задачи от HTTP submit до draft PR.

## Existing AIOS Architecture (использовано, не изменено)

- `aios_core/orchestrator.py` (protected) — канонические `Task`/`TaskStatus`: контур
  использует их как носитель (`TaskExtras` — отдельная сущность, правки не было).
- `aios_core/self_protection.py` (protected) — protected/deny списки: контур
  проверяет diff против них, не расширяя.
- `aios_core/audit_logger.py` — канонический аудит с маскированием: обёрнут в `OHAuditLogger`.
- octopus `agent_orchestrator_api` — реестр агентов: расширен полями контура (F4).
- octopus state-механизм (`OCTOPUS_ORCHESTRATOR_STATE_DIR`) — тот же каталог для `ContourStore`.

## What Was Added (по фазам)

| Фаза | PR | Добавлено |
|---|---|---|
| F1 | #218 | `client.py`, `errors.py` — Cloud API v1 клиент (разговоры, start-task, ожидание, события), иерархия ошибок |
| F2 | #219 | `models.py` (роли/гейты/TaskExtras/FailureReport), `permissions.py` (профили + check_paths), `profiles.py` (build_prompt) |
| F3 | #220 | `state_machine.py` (переходы/гейты/лимит retry), `audit.py` (OHAuditLogger) |
| F4 | #221 | octopus-реестр: role/permissions/allowed_paths (расширение существующего, не новый реестр) |
| F5 | #222 | `github.py` (GitRunner без shell + GitHubHelper: ветка/commit/diff/push/PR), `runner.py` (OHOrchestrator — MVP lifecycle, retry ≤3, FailureReport, finalize с deny-paths + draft PR) |
| F6 | #223 | `verdicts.py` (parse_review_verdict), `service.py` (ContourService: submit/run/status) |
| F7 | #224 | `store.py` (ContourStore — персистентность), service на store + restore |
| F8 | #225 | `api.py` (FastAPI router `/api/v1/oh-contour`: submit/run/status/verdict, токен-авторизация) |
| F9 | #226 | docs: OPENHANDS_INTEGRATION, AIOS_AGENT_ARCHITECTURE, TASK_LIFECYCLE, SECURITY_MODEL, TESTING_AGENT_SYSTEM |
| F10 | #227 | `.agents/skills/oh-contour-{architecture,testing,security}` |

## What Was Modified

- `octopus_core/agent_orchestrator_api.py` (F4) — поля role/permissions/allowed_paths
  (обратно-совместимо, опциональные).
- `.gitignore` — `.oh_contour/` (repo-local fallback state).
- Protected-файлы, публичный API, существующие сервисы — **не изменены**.

## Agent Architecture

Роли (`models.AgentRole`): MVP — orchestrator/architect/coder/tester/reviewer;
подключены профилями security/qa и (post-F11) devops/android/ml/research/documentation.
Роль = `AgentProfile` (RBAC-имя, read/write, allowed_paths) + self-contained промпт
(`build_prompt`). Разговоры изолированы, контур склеивает их состоянием задачи.

## OpenHands Integration

Cloud-клиент (env `OPENHANDS_API_KEY`), вердикт Reviewer из событий разговора
(маркеры, консервативно), GitHub через subprocess+REST (env `GITHUB_TOKEN`),
HTTP API с токеном. Конфигурация — только env; секреты не в коде/state/логах.

## Skills

Три repository skill в `.agents/skills/` (AgentSkills формат): architecture
(модули, protected-правило, расширение), testing (без моков, сценарии, запуск),
security (секреты/права/diff/HTTP/аудит, порядок при находке).

## Task System

Каноническая `orchestrator.Task` (не изменена) + контурные `TaskExtras`
(ветка, гейты, retry, conversation_ids, артефакты) + `ContourTask` (связка с
RunResult). `ContourService` — входная точка; `ContourStore` — персистентность
(JSON, env-цепочка state dir, repo-local fallback); задачи переживают рестарт.

## State Machine

`OHStatus` (READY/TESTING/REVIEW/SECURITY_REVIEW/QA/BLOCKED поверх TaskStatus),
таблица переходов, гейты засчитываются при выходе из стадии, лимит retry
(исчерпание → CANCELLED + FailureReport), `TransitionError` — баг контура,
не retry-able. Маршрут: `PENDING→PLANNING→READY→RUNNING→TESTING→REVIEW(→SECURITY→QA)→COMPLETED`.

## Git Workflow

Feature-ветки `agent/oh-fN-*` (main не тронут), коммиты с `Co-authored-by`,
draft PR на каждую фазу, coordination-журнал сессии. Стек PR: #218→…→#227
(мержить по порядку или вместе). В runner: finalize = diff-проверка + draft PR.

## Security

Профили ролей с allowed_paths, check_paths против protected/deny в finalize,
гейты перед COMPLETED, лимит retry, HTTP-токен (401), маскирование аудита,
git без shell, консервативный вердикт. Риски на владельце: дефолтный токен,
нет per-user auth, Cloud-ключ в env процесса. Подробно: `docs/SECURITY_MODEL.md`.

## Tests

114 тестов контура (`tests/test_openhands_*.py`) + octopus-регресс 8 — **131/131**,
ruff чист. Принципы: без моков внешних систем (реальный git/HTTP/audit/store),
fake только Cloud-клиент (`FakeClient`), DI для сети. Покрытие: клиент, модели,
permissions, профили, state machine, аудит, github, runner (8 сценариев), service,
store (рестарт), api (auth/404/flow).

## Known Problems

1. Реальный прогон против OpenHands Cloud не выполнялся (нет ключа) — контракт
   проверен fake-клиентом по протоколу `ConversationClient`.
2. HTTP `run` синхронный — длинные lifecycle блокируют запрос.
3. State-файл без атомарной записи/lock — при первой реальной конкуренции.
4. ~~Роутер не смонтирован~~ — смонтирован в `create_app` (sub-app `Mount`) и `main.py`
   (post-F11); выключается env `OH_CONTOUR_HTTP_ENABLED=0`.

## Remaining Work

- ~~Реальный E2E~~ (выполнен post-F11: задача `e9079198ebf8` → 4 Cloud-разговора → draft PR #231).
- ~~Монтирование router в host-приложение~~ (выполнено post-F11).
- ~~Асинхронный run (фоновая задача + polling status)~~ и ~~атомарная запись state~~
  (выполнено post-F11: run_task_async + run-lock; tmp+os.replace).
- ~~Профили и промпты остальных 5 ролей~~ (выполнено post-F11: доменные allowed_paths + RBAC + инструкции).

## Recommended Next Steps

1. Мерж стека #218–#227 (по порядку или squash).
2. Production env на хосте (`OH_CONTOUR_TOKEN`, `OH_CONTOUR_REPO`, ключи).
3. Первый реальный E2E на безопасной микрозадаче (docstring/типы) — проверка всей цепочки.
4. По результатам E2E: async run, атомарный state, профили остальных ролей.
