---
name: geo-aware-routing
description: Optimizes swarm traffic based on geographic location and latency.
---

# SKILL: geo-aware-routing
**Category:** core
**Status:** ACTIVE (on-demand)
**Created:** 2026-06-20 (Batch #91, Phase 11/12)
**Path:** /opt/octopus-geo-routing.py
**Data:** /var/lib/octopus/geo-routing/routing_table.json

## Description
Optimizes swarm traffic based on geographic location and latency.
Maps nodes to regions (eu-west, eu-central, us-east, asia-east).
Builds routing tables sorted by latency and cost.

## Commands
- Build table: `python3 /opt/octopus-geo-routing.py`
- View routes: `cat /var/lib/octopus/geo-routing/routing_table.json | jq`

## Integration
Part of Phase 11/12: Geo-Aware Routing (Global Swarm optimization)
Feeds from: mesh_nodes.json, discovery data

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
- Описание назначения: Операционный навык Octopus: geo-aware-routing.
