---
name: creative-evolution
version: 1.0
description: Автогенерация эволюционных сводок из системных данных, опыта и метрик
triggers: [evolution_report, periodic_summary]
dependencies: []
llm_required: true
mcp_tools: []
---

# SKILL: creative-evolution
**Category:** core
**Status:** ACTIVE (on-demand)
**Created:** 2026-06-20 (Batch #91, Phase 5)
**Path:** /opt/octopus-creative-evolution.py
**Report:** /var/lib/octopus/evolution/evolution_report.json

## Description
Auto-generates evolutionary summaries from system data, experience, and metrics.
Tracks memory growth, reputation evolution, BFT consensus, skill ecosystem, federation progress.
Produces narrative reports of system development trajectory.

## Commands
- Run report: `python3 /opt/octopus-creative-evolution.py`
- View summary: `cat /var/lib/octopus/evolution/latest_summary.md`
- View data: `cat /var/lib/octopus/evolution/evolution_report.json`

## Integration
Part of Phase 5: Creative Evolution Reporting (Auto-summaries)
Feeds from: All system components (forecaster, BFT, reputation, barter, etc.)

## Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2. Классифицировать навык по тегам (health/api/memory/disk/telegram/systemd/docker/security/ai).
3. Выполнить только безопасные read-only проверки через `code/run.py` и общий `generic_skill_runtime`.
4. Сформировать JSON-отчёт: статус, найденные факты, риски, рекомендации, следующий bounded-шаг.
5. Если требуется изменение системы — записать proposal/rollback в logs/reports и ждать consent gate либо выполнения автономным агентом в bounded-режиме.
6. Для Telegram: прямые push-уведомления запрещены, кроме `skill-notification` и отчётов автономного агента.
7. Для AWS/платных ресурсов: только аудит; создание/включение ресурсов запрещено без явной команды человека.

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py` пересчитывает health/coverage и дописывает AI-предложения в `references/`.
- Развитие через ИИ: локальный Ollama/Qwen генерирует bounded improvement proposal; автоприменяются только безопасные структурные улучшения (алгоритм, тест, runtime wrapper).
- Описание назначения: Операционный навык Octopus: creative-evolution.
