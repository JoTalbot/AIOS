---
name: oh-contour-architecture
description: OpenHands-контур AIOS — архитектура, модули и расширение. Использовать при изменении aios_core/openhands/*, добавлении ролей/стадий, интеграции с orchestrator/octopus.
---

# OpenHands-контур: архитектура

## Ключевое правило

AIOS владеет оркестрацией/состоянием/правами/аудитом; OpenHands Cloud — исполнением.
Protected-файлы (`run_coder_orchestrator*.py`, `aios_core/orchestrator.py`,
`aios_core/self_protection.py` — полный список `self_protection.PROTECTED_PATTERNS`)
НЕ изменять: контур — отдельный пакет, интеграция через использование, не правку.

## Модули (`aios_core/openhands/`)

`client` (Cloud API) · `errors` · `models` (AgentRole/Gate/TaskExtras/FailureReport) ·
`permissions` (профили + check_paths) · `profiles` (build_prompt) · `state_machine`
(переходы/гейты/лимит) · `runner` (lifecycle) · `verdicts` · `github` (branch/PR) ·
`store` (персистентность) · `service` (ContourService — вход) · `api` (FastAPI router) ·
`audit` (OHAuditLogger).

## Перед изменением

1. Прочитать `docs/AIOS_AGENT_ARCHITECTURE.md` и `docs/TASK_LIFECYCLE.md`.
2. Найти существующую реализацию (не создавать дубликат).
3. Изменение таблицы переходов → обновить `docs/TASK_LIFECYCLE.md` и тесты state machine.
4. Новая роль → профиль в `permissions.PROFILES` + промпт в `profiles.py` + тест.
5. Новый гейт/стадия → `Gate`, `_TRANSITIONS`, `_STAGE_GATE`, `_stage_of` в runner + тесты.

## Проверка

```bash
python3 -m pytest tests/test_openhands_*.py -p no:cacheprovider
python3 -m ruff check aios_core/openhands/
```
