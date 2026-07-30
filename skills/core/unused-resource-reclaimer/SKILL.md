---
name: unused-resource-reclaimer
version: 1.0
description: Безопасный сканер системы для неиспользуемых ресурсов
triggers: [periodic_check, disk_alert]
dependencies: [skill-health-monitor]
llm_required: false
mcp_tools: []
---

# SKILL: unused-resource-reclaimer
**Category:** core
**Status:** ACTIVE (on-demand + dry-run safe)
**Created:** 2026-06-20 (Batch 85, Phase 8 upgrade)
**Path:** /opt/octopus-resource-reclaimer.py
**Report:** /var/lib/octopus/reclaimer/last_report.json

## Description
Scans system for unused resources and reports them safely.
Targets: old .bak files, orphaned processes, stale services, empty dirs, old docker images.
NEVER touches: system logs, iteration logs, project files, or any SAFE_PATH.

## Commands
- Dry-run scan: `python3 /opt/octopus-resource-reclaimer.py --dry-run`
- Full scan (reports only): `python3 /opt/octopus-resource-reclaimer.py`
- View report: `cat /var/lib/octopus/reclaimer/last_report.json`

## Safe Paths
System logs, project files, SSH keys, and all core /opt scripts are protected.

## Integration
Part of Phase 8: Unused Resource Reclaimer (Hyper-efficiency)

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
- Описание назначения: Операционный навык Octopus: unused-resource-reclaimer.
