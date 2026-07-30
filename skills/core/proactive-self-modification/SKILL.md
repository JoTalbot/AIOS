---
name: proactive-self-modification
version: 1.0
description: Проактивная система детекции аномалий и самокоррекции
triggers: [periodic_30min, anomaly_detected]
dependencies: [skill-health-monitor, unused-resource-reclaimer]
llm_required: true
mcp_tools: []
---

# SKILL: proactive-self-modification
**Category:** core
**Status:** ACTIVE (on-demand + systemd timer 30min)
**Created:** 2026-06-20 (Batch 85, Phase 8)
**Path:** /opt/octopus-proactive-self-mod.py
**Journal:** /var/lib/octopus/self-modification/journal.json
**Consent:** /var/lib/octopus/human_consent.env

## Description
Proactive anomaly detection and self-modification system. Integrates with the Load Forecaster and Resource Reclaimer to detect system anomalies, generate fix patches, enforce consent gates before applying changes, and maintain an autonomy journal.

## Detection Targets
- Disk usage (warning > 80%, critical > 90%)
- Memory usage (warning > 85%)
- Load average (warning > 3.0)
- Orphaned/failed systemd services
- Disk space trending

## Safety Features
- Consent gate check before any live changes
- Dry-run mode by default (--dry-run flag)
- Journal records all decisions and patches
- Integration with Instructions #08, #09, #13, #18

## Commands
- Dry-run scan: python3 /opt/octopus-proactive-self-mod.py --dry-run
- Live scan: python3 /opt/octopus-proactive-self-mod.py
- View journal: cat /var/lib/octopus/self-modification/journal.json

## Integration
Part of Phase 8: Proactive Self-Modification protocols
Feeds from: Forecaster (8.1), Reclaimer (8.3)
Feeds to: Autoheal (#20), Swarm coordination (#19)

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
- Описание назначения: Операционный навык Octopus: proactive-self-modification.
