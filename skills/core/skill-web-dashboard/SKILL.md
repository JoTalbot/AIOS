---
name: skill-web-dashboard
version: 3.0
description: Веб-дашборд статуса проекта Octopus с метриками и доступами
triggers: [http_request, web_access]
dependencies: [skill-health-monitor]
llm_required: false
mcp_tools: []
---
# Skill Web Dashboard

## Описание
Простой HTTP сервер, отдающий HTML-дашборд с текущим состоянием проекта Octopus.
Содержит: здоровье, скиллы, ноды, доступы, дашборды, инструкции по восстановлению.

## Алгоритм
1. Запустить HTTP сервер на порту 8080
2. При запросе собрать данные из health_monitor, skills_loader, autonomy_state
3. Отдать HTML страницу

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
