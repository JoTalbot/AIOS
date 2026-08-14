# Сессия: единый источник версии

---
session_id: "20260814T090000Z-aios-arena-version-consistency"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T09:00:00Z"
updated_utc: "2026-08-14T09:00:00Z"
branch: "agent/20260814-version-consistency"
base_commit: "96ead91e"
claim: "coordination/claims/version-consistency--20260814T090000Z-aios-arena-version-consistency.md"
---

## Цель

Устранить дрейф package/API/docs version без произвольного изменения канонической версии 19.9.0 и добавить автоматическую проверку согласованности.

## Scope

- Разрешено: version helper, `main.py`, version-related docs/workflow, целевые тесты.
- Вне scope: LLM proxy, deployment manifests, systemd runtime, dependency consolidation.
- Пересечения: не ожидаются; работа ведётся в отдельном worktree.

## Исходное состояние

- `VERSION` и `pyproject.toml`: 19.9.0.
- `main.py` и `ARCHITECTURE.md`: 16.0.0.
- `docs/STATUS.md` и docs workflow: 9.3.0.
- Runtime service labels содержат v20/v21 и рассматриваются как версии отдельных rollout-контуров, не как основание для package bump.
- В основном `/root/AIOS` есть чужие изменения LLM proxy; этот worktree их не содержит.

## План

1. Ввести небольшой безопасный reader канонического `VERSION`.
2. Подключить FastAPI metadata и docs publication к источнику истины.
3. Явно пометить исторические документы вместо подмены их метрик.
4. Добавить тесты согласованности и прогнать целевые/полные безопасные проверки.

## Ход работы и решения

- Каноническая версия остаётся 19.9.0 до отдельного release decision владельца.

## Изменённые файлы

Пока только session/claim.

## Проверки

- `[NOT RUN]` — реализация ещё не начата.

## Git

- Коммиты: claim commit.
- Незакоммиченные изменения: нет на старте.
- Чужие изменения в основном worktree не затронуты.

## Handoff

- Последняя завершённая точка: создан изолированный worktree и scope.
- Следующий конкретный шаг: исследовать безопасный способ чтения `VERSION` без import side effects.
- Блокеры: нет.
- Риски: импорт `main.py` имеет широкие side effects; тестировать version binding без запуска production компонентов.
