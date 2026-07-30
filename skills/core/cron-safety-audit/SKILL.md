---
name: cron-safety-audit
version: 2.0
description: Проверяет cron/systemd-timer правила на безопасность и конфликты
triggers: [cron_audit, cron_daily]
dependencies: []
llm_required: false
---
# SKILL: cron-safety-audit

## Описание
Проверяет cron jobs и systemd timers на безопасность, конфликты
и потенциальные проблемы: перекрывающиеся расписания, небезопасные команды,
отсутствие timeout, избыточная частота.

## Алгоритм
1. Собрать все cron jobs (user + system)
2. Собрать все systemd timers
3. Проверить на конфликты расписания
4. Проверить на небезопасные команды (rm, chmod, etc.)
5. Проверить на отсутствие timeout
6. Сформировать отчёт с рекомендациями

## Контроль и развитие
- Runtime: `code/run.py --json`
- Contract tests: `tests/test_contract.py`
