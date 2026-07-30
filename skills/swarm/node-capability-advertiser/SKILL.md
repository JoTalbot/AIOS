---
name: node-capability-advertiser
description: На каждой ноде периодически публикует свои текущие возможности и состояние в capability-registry и федерацию.
---
# Node Capability Advertiser

## Описание

Этот скил предназначен для...

## Workflow (на каждой ноде)
1. Собрать:
   - Список установленных скриптов/моделей
   - Список запущенных процессов
   - Доступные ресурсы (из /proc, docker stats и т.д.)
   - Активные скиллы (из local skills loader)
2. Отправить в capability-registry (локально + по P2P)
3. Периодичность: каждые 30-60 сек + по событиям (install, start, stop)

## Интеграция
- capability-registry
- p2p-federation
- node-health-orchestrator

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
- Описание назначения: На каждой ноде периодически публикует свои текущие возможности и состояние в capability-registry и федерацию.
