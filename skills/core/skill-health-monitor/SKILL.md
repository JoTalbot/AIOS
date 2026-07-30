---
name: skill-health-monitor
version: 3.0
description: Мониторинг здоровья системы Octopus — SLO, disk, services, Docker, memory
triggers: [health_check, cron_5min, autonomous_agent_cycle]
dependencies: []
llm_required: false
mcp_tools: []
---
# Skill Health Monitor

## Описание
Автоматический мониторинг здоровья всех компонентов системы Octopus.
Проверяет SLO, disk usage, systemd services, Docker containers, memory pool, и формирует отчёт.

## Входные данные
- Не требуются (автономный сбор)

## Выходные данные
- JSON отчёт здоровья: {status, slo, disk, services, docker, memory, score}
- Возвращает оценку здоровья 0-1000

## Алгоритм
1. Проверить disk usage через df
2. Проверить systemd services через systemctl
3. Проверить Docker containers через docker ps
4. Проверить SLO (если доступен octopus CLI)
5. Проверить orphan processes
6. Вычислить health score
7. Вернуть JSON отчёт

## Опыт
- Первая имплементация 2026-06-24
- Все 221 скилл были заглушками — нужен реальный мониторинг

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
