---
name: context-fundamentals
description: Attention budget, U-curve, progressive disclosure, position-aware placement. Foundation for all memory/RAG decisions. Use when designing context for packstore, swarm agents.
---
# Context Fundamentals (murat adapted)

## Описание

Этот скил предназначен для...
## Core Principles
1. Informativity over exhaustiveness
2. Position-aware (beginning/end strongest)
3. Progressive disclosure (metadata → body → refs)
4. Iterative curation
## For Octopus
- CAS objects: keep identifiers, load on demand
- RAG: edge-position critical facts
- Swarm: isolate context per sub-agent

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
- Описание назначения: Attention budget, U-curve, progressive disclosure, position-aware placement. Foundation for all memory/RAG decisions. Use when designing context for packstore, swarm agents.
