---
name: skill-autonomous-agent
version: 3.0
description: Автономный ИИ-агент постоянного развития проекта Octopus по всем векторам
triggers: [autonomous_cycle, timer_30min]
dependencies: [skill-health-monitor, skill-notification, skill-task-decompose, skill-schedule-runner]
llm_required: true
mcp_tools: []
---
# Skill Autonomous Agent

## Описание
Автономный ИИ-агент, который постоянно работает над развитием проекта Octopus
по всем 8 векторам (ПАМЯТЬ > ЖИТЬ > УПРОЩЕНИЕ > СОСУЩЕСТВОВАНИЕ > РАЗМНОЖАТЬСЯ > РАЗВИВАТЬСЯ > УЧИТЬСЯ > МЕНЯТЬСЯ).

## Алгоритм (цикл каждые 30 минут)
1. ЗАГРУЗКА КОНТЕКСТА — прочитать COMPACT_CONTEXT, логи, опыт
2. ПРОВЕРКА ЗДОРОВЬЯ — health check системы
3. ПЛАНИРОВАНИЕ — выбрать следующую задачу по векторам
4. ИСПОЛНЕНИЕ — выполнить одну bounded задачу
5. ОЦЕНКА — проверить результат
6. ОТЧЁТ — записать лог, уведомить человека

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
