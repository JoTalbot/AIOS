---
name: cost-anomaly-reader
version: 2.0
description: Выявляет аномальные расходы в облачных аккаунтах (read-only)
triggers: [cost_audit, cron_daily]
dependencies: []
llm_required: false
---
# SKILL: cost-anomaly-reader

## Описание
Выявляет аномальные расходы и usage в облачных аккаунтах (read-only).
Проверяет AWS billing, Docker Hub usage, и другие потенциальные расходы.
Важно: только чтение, инструкция #08 — никаких платных действий.

## Алгоритм
1. Проверить AWS cost (если доступно)
2. Проверить Docker Hub usage
3. Проверить Railway usage
4. Проверить disk I/O anomalies
5. Сформировать отчёт

## Контроль и развитие
- Runtime: `code/run.py --json`
- Contract tests: `tests/test_contract.py`
