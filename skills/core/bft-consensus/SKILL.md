---
name: bft-consensus
description: 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
---

# SKILL: bft-consensus
**Category:** core | **Status:** ACTIVE | **Phase:** 1 A3 + Phase 2
**Path:** /opt/octopus-bft-consensus.py | **Data:** /var/lib/octopus/bft/
**Description:** Byzantine Fault Tolerance consensus for swarm nodes. Tolerates f faulty nodes in 3f+1 swarm. Proposals: scale, evict, config updates.
**Commands:** python3 /opt/octopus-bft-consensus.py
**Results:** 4 nodes, f=1, quorum=3, all proposals committed

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
- Описание назначения: Операционный навык Octopus: bft-consensus.
