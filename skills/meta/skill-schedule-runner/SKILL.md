---
name: skill-schedule-runner
version: 3.0
description: Выполнение запланированных задач по расписанию (вдохновлён Hermes cron)
triggers: [cron_trigger, timer_fire]
dependencies: [skill-health-monitor, skill-notification]
llm_required: false
mcp_tools: []
---
# Skill Schedule Runner

## Описание
Выполняет запланированные задачи по расписанию. Поддерживает интервалы и фиксированное время.
Вдохновлён cron-системой Hermes Agent.

## Алгоритм
1. Прочитать расписание из config
2. Определить какие задачи пора запускать
3. Выполнить каждую задачу
4. Зафиксировать результат
5. Отправить уведомление

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
