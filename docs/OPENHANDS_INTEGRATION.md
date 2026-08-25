# Интеграция OpenHands (Cloud API) в AIOS

AIOS владеет оркестрацией, состоянием задач, правами и аудитом; OpenHands Cloud —
исполнением в sandbox. Роли контура (Architect/Coder/Tester/Reviewer/...) — профили
OpenHands-разговоров, а не новые классы агентов AIOS. План: `AIOS_OPENHANDS_INTEGRATION_PLAN.md`.

## Модули (`aios_core/openhands/`)

| Модуль | Назначение |
|---|---|
| `client.py` | `OpenHandsClient` — тонкая обёртка Cloud API v1: разговоры, start-task, ожидание, события |
| `errors.py` | Иерархия ошибок: `OpenHandsError` → API/Auth/Start/Timeout/Configuration |
| `models.py` | `AgentRole` (11 ролей, `MVP_ROLES` — первые 5), `Gate`, `TaskExtras`, `FailureReport`, `ReviewDecision` |
| `permissions.py` | Профили ролей (read/write/allowed_paths), `check_paths` против protected/deny из `self_protection` |
| `profiles.py` | `build_prompt` — initial_message разговора роли (инструкция + задача + контекст) |
| `state_machine.py` | `OHStatus`, таблица переходов, `transition()` — гейты засчитываются при выходе из стадии, лимит retry |
| `runner.py` | `OHOrchestrator` — MVP lifecycle задачи (см. `docs/TASK_LIFECYCLE.md`) |
| `verdicts.py` | `parse_review_verdict` — маркеры `APPROVED`/`CHANGES_REQUESTED` в событиях разговора |
| `github.py` | `GitRunner` (subprocess без shell) + `GitHubHelper` (ветка/коммит/diff/push/PR) |
| `store.py` | `ContourStore` — JSON-персистентность задач (переживают рестарт) |
| `service.py` | `ContourService` — входная точка: `submit`/`run_task`/`status`; связка с канонической `orchestrator.Task` |
| `api.py` | FastAPI router `/api/v1/oh-contour` (HTTP поверх сервиса) |
| `audit.py` | `OHAuditLogger` — события контура в канонический `AuditLogger` (маскирование секретов) |

## Переменные окружения

| Переменная | Назначение | Default |
|---|---|---|
| `OPENHANDS_API_KEY` | Ключ Cloud API | — (обязательна для client) |
| `GITHUB_TOKEN` | Токен для GitHub PR | — (без него PR-стадия пропускается) |
| `OH_CONTOUR_REPO` | `owner/repo` для разговоров и PR | — |
| `OH_CONTOUR_WORKSPACE` | Локальный workspace для git | `.` |
| `OH_CONTOUR_TOKEN` | Токен HTTP API | → `OCTOPUS_TOKEN` → `default` |
| `OH_CONTOUR_STATE_DIR` | Каталог state-файла | → `OCTOPUS_ORCHESTRATOR_STATE_DIR` → `/var/lib/aios/oh_contour` → repo-local `.oh_contour/` |

Секреты только в env; в коде, логах и state-файле не хранятся (аудит маскирует).

## HTTP API

Router `oh_contour_router` смонтирован:
- прод-API (`aios_core.api.app.create_app`, Starlette): FastAPI sub-app через
  `Mount("/")` (FastAPI APIRoute требует middleware context), выключается
  env `OH_CONTOUR_HTTP_ENABLED=0`;
- `main.py` (NiceGUI): `app.include_router(oh_contour_router)`.

Авторизация: заголовок `x-octopus-token` (как в octopus orchestrator).

| Метод | Путь | Ответ |
|---|---|---|
| `POST` | `/api/v1/oh-contour/tasks` | 201 `{ok, task_id}`; 422 на пустой title/неизвестный gate |
| `POST` | `/api/v1/oh-contour/tasks/{id}/run` | `{ok, result}` — RunResult + FailureReport |
| `GET` | `/api/v1/oh-contour/tasks/{id}` | сводный статус (404 на неизвестный id) |
| `GET` | `/api/v1/oh-contour/tasks/{id}/verdict` | `{review_decision}` |

Пример:

```bash
curl -X POST "$AIOS/api/v1/oh-contour/tasks" \
  -H "x-octopus-token: $OH_CONTOUR_TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "Добавить docstring в module.py", "required_gates": ["tests", "review"]}'
```

## Governed production-вход

Прямой `ContourService.run_task()` остаётся внутренним/legacy API. Для запуска Cloud-задач
в production использовать `aios_core.architecture.GovernedOpenHandsRunner`: capability
`openhands_cloud_run` проходит Policy Kernel, explicit human approval, lifecycle,
heartbeat, budget, Execution Kernel и hash-chained audit до первого Cloud side effect.
HTTP router пока вызывает legacy service напрямую и **не готов для production Cloud run**
до переноса на governed runner.

## Программный вход (legacy/internal)

```python
from aios_core.openhands import ContourService, OpenHandsClient

service = ContourService(client=OpenHandsClient(), repository="org/repo")
task_id = service.submit("Сделать X", "Описание X")
result = service.run_task(task_id)   # RunResult: status, pr_url, report
```

## Что осознанно НЕ реализовано

- Реальный прогон против OpenHands Cloud (все тесты — fake-клиент по протоколу runner)
- Асинхронный запуск `run` (сейчас синхронный)
- Атомарная запись state (tmp+rename) и file-lock — при первой реальной конкуренции
- Protected-файлы (`run_coder_orchestrator*.py`, `aios_core/orchestrator.py` и др.) не изменены:
  контур — отдельный пакет, интеграция через реестр octopus (F4) и `orchestrator.Task`
