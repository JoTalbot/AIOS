---
name: dynamic-capability-sync
description: Синхронизирует информацию о возможностях и текущем состоянии инструментов между нодами через MCP, P2P и федерацию (Nostr/Matrix). Обеспечивает一致ность реестра.
---
# Dynamic Capability Sync

## Описание

Этот скил предназначен для...

## Задачи
- Периодически синхронизировать capability-registry между нодами
- Распространять решения dynamic-tool-orchestrator
- Обновлять глобальное представление "что где запущено"
- Работать поверх p2p-federation и MCP

## Интеграция
- capability-registry
- p2p-federation
- mcp-server-expose
- dynamic-tool-orchestrator

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
- Описание назначения: Синхронизирует информацию о возможностях и текущем состоянии инструментов между нодами через MCP, P2P и федерацию (Nostr/Matrix). Обеспечивает一致ность реестра.
