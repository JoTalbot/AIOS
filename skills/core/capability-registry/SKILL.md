---
name: capability-registry
description: Реестр возможностей каждой ноды (какие инструменты/скрипты/модели могут быть установлены и запущены). Динамически обновляется.
---
# Capability Registry

## Что хранит
Для каждой ноды:
- Установленные инструменты и версии
- Запущенные процессы/сервисы
- Доступные ресурсы (CPU, RAM, GPU, disk)
- Поддерживаемые скиллы (из loader)
- Текущая нагрузка и "специализация" ноды

## Операции
- register_capability(node_id, capability)
- get_node_capabilities(node_id)
- get_best_nodes_for(capability, count=1)
- update_node_load(node_id, metrics)

## Интеграция
- node-capability-advertiser (публикует локальные возможности)
- dynamic-tool-orchestrator (читает при принятии решений)
- load-aware-scheduler
- script-deployer (обновляет после install/uninstall)

## Описание
Базовое описание функционала.

## Инструкции
1. Изучить код.
2. Выполнить проверку.

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
- Описание назначения: Реестр возможностей каждой ноды (какие инструменты/скрипты/модели могут быть установлены и запущены). Динамически обновляется.
