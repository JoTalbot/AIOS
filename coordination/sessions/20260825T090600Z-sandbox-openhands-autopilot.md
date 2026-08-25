---
session_id: "20260825T090600Z-sandbox-openhands-autopilot"
status: "ACTIVE"
agent: "OpenHands sandbox agent"
machine: "openhands-workspace"
started_utc: "2026-08-25T09:06:00Z"
updated_utc: "2026-08-25T09:06:00Z"
branch: "auto/openhands/autopilot-20260825"
base_commit: "ad5bda0"
claim: "coordination/claims/autopilot--20260825T090600Z-sandbox-openhands-autopilot.md"
---

## Цель

Автономный генератор задач для OpenHands-контура: скан ассортимента проекта
(TODO/FIXME, ruff) → упорядоченная очередь → `ContourService.submit/run_task`.

## Scope

- Разрешённые компоненты/файлы: `scripts/openhands_autopilot.py`,
  `tests/test_openhands_autopilot.py`, координация.
- Явно вне scope: protected-файлы, правки контура `aios_core/openhands/`.

## План

1. Коллекторы `todo`/`ruff` — чистые функции, детерминированный порядок.
2. CLI: `--plan` (по умолчанию, безопасно) / `--run` (исполнение через Cloud-клиент).
3. Тесты (fake-клиент), pytest + ruff.

## Текущий шаг (виден другим агентам)

- Текущий шаг: DONE — автопилот реализован и проверен.
- Обновлено UTC: 2026-08-25T09:20:00Z

## Ход работы и решения

- Коллекторы `todo` (TODO/FIXME по файлам) и `ruff` (через `shutil.which`,
  fallback `python -m ruff`) выдают `TaskDraft`; детерминированный порядок
  ruff → todo. Подача `submit_queue` пропускает дубликаты по заголовку и
  соблюдает `--max-tasks`.
- CLI: по умолчанию безопасный `--plan`; `--run` строит реальный
  `OpenHandsClient` (env `OPENHANDS_API_KEY`) и последовательно исполняет задачи.
- `sys.path`-правка как в `selfguard.py` для прямого запуска скрипта.

## Изменённые файлы

- `scripts/openhands_autopilot.py` — автопилот.
- `tests/test_openhands_autopilot.py` — 10 тестов (fake-клиент).
- координация — журнал/claim.

## Проверки

- `[PASS]` `python -m pytest tests/test_openhands_autopilot.py -q` — 10/10.
- `[PASS]` `python -m pytest tests/test_openhands_service.py -q` — интеграция clean.
- `[PASS]` `python -m pytest tests/test_openhands_*.py -q` — весь набор контура.
- `[PASS]` `python -m ruff check` обоих файлов.
