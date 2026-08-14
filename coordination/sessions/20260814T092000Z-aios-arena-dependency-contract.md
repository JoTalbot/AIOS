# Сессия: dependency contract и воспроизводимый lock

---
session_id: "20260814T092000Z-aios-arena-dependency-contract"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T09:20:00Z"
updated_utc: "2026-08-14T09:20:00Z"
branch: "agent/20260814-dependency-contract"
base_commit: "3c53eb12"
claim: "coordination/claims/dependency-contract--20260814T092000Z-aios-arena-dependency-contract.md"
---

## Цель

Определить роли dependency-файлов, устранить конфликт metadata/production lock и добавить автоматический воспроизводимый контракт без массового обновления пакетов.

## Scope

- Разрешено: `pyproject.toml`, direct requirements input, policy, read-only checker и тесты.
- Вне scope: массовый upgrade 198 lock-пакетов, Docker rebuild, runtime venv mutation.
- Отдельный worktree; чужая LLM-работа не затрагивается.

## Исходное состояние

- `pyproject.toml`: 12 minimal package dependencies.
- `requirements.txt`: 45 full production direct dependencies.
- `requirements.lock`: 198 exact resolved packages, Dockerfile устанавливает lock.
- `requests` и `python-dotenv` были core metadata, но не direct production input.
- `websockets>=16.1.1` в metadata конфликтовал с `web3 7.16.0`, который требует `websockets<16`; production lock содержит 15.0.1.
- Временный pip-compile с диапазоном `websockets>=15,<16` воспроизвёл все 198 текущих pins без изменений.

## План

1. Согласовать direct constraints и core metadata с валидным lock.
2. Формально описать minimal/full/lock/dev роли.
3. Добавить checker: direct/core subset, exact pins, specifier satisfaction, Docker lock usage.
4. Проверить pip-compile в temp и целевые тесты.

## Handoff

- Последняя точка: найден и воспроизведён dependency conflict.
- Следующий шаг: реализовать contract checker.
- Блокеры: нет.
