---
name: skill-task-decompose
version: 3.0
description: Декомпозиция задач на подзадачи с приоритизацией по векторам развития
triggers: [task_received, autonomous_agent_plan]
dependencies: [skill-health-monitor]
llm_required: true
mcp_tools: []
---
# Skill Task Decompose

## Описание
Декомпозирует задачу на подзадачи, распределяет по векторам развития (#05, #11),
оценивает сложность и время выполнения, учитывает текущее состояние системы.

## Входные данные
- task_description: описание задачи
- context: текущий контекст (health report, TODO list)

## Выходные данные
- JSON с подзадачами, приоритетами, зависимостями, векторами

## Алгоритм
1. Получить health report от skill-health-monitor
2. Прочитать MASTER_TODO
3. Определить вектор задачи (ПАМЯТЬ > ЖИТЬ > УПРОЩЕНИЕ > ...)
4. Декомпозировать задачу на шаги
5. Оценить риски каждого шага
6. Вернуть план с priority ordering

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
