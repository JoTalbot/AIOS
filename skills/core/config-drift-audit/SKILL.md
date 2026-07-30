---
name: config-drift-audit
version: 2.0
description: Обнаруживает расхождения (drift) между конфигами и каноническим состоянием
triggers: [config_audit, cron_30min]
dependencies: []
llm_required: false
---
# SKILL: config-drift-audit

## Описание
Обнаруживает расхождения между текущими конфигами и каноническим/ожидаемым состоянием.
Проверяет systemd units, nginx configs, Docker compose, environment files,
octopus configs и формирует drift-отчёт.

## Алгоритм
1. Определить набор канонических конфиг-путей для мониторинга
2. Считать текущие значения (checksums, settings)
3. Сравнить с предыдущим снимком (если есть)
4. Классифицировать drift: critical (security), warning (functional), info (cosmetic)
5. Сформировать отчёт с рекомендациями по устранению

## Контроль и развитие
- Runtime: `code/run.py --json`
- Contract tests: `tests/test_contract.py`
