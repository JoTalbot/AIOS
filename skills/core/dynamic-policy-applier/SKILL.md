---
name: dynamic-policy-applier
description: Применяет политики из policy-engine к текущему desired-state и инициирует reconcile через dynamic-tool-orchestrator. Мост между правилами и действиями.
---
# Dynamic Policy Applier

## Описание

Этот скил предназначен для...

## Workflow
1. Загружает активные политики из policy-engine
2. Применяет их к tool-desired-state
3. Вызывает dynamic-tool-orchestrator для приведения системы в соответствие
4. Логирует какие политики сработали и какие изменения были применены

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
- Описание назначения: Применяет политики из policy-engine к текущему desired-state и инициирует reconcile через dynamic-tool-orchestrator. Мост между правилами и действиями.
