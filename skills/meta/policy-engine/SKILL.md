---
name: policy-engine
description: "Гибкий движок политик для динамического распределения инструментов. Позволяет задавать сложные правила: \"в development mode на всех бесплатных нодах выключить всё тяжелое\", \"на нодах с GPU приоритет отдавать inference\", \"при нагрузке > 80% переносить задачу\". Используется dynamic-tool-orchestrator."
---
# Policy Engine

## Описание

Этот скил предназначен для...

## Возможности
- Правила в YAML/JSON
- Условия: режим, нагрузка, тип ноды (free-tier / third-party), время суток, consent status
- Действия: require, prefer, forbid, scale, move
- Приоритет политик
- Аудит и объяснение решений

## Примеры правил
- development_mode:
    when: mode == "development"
    action: stop heavy_models whisper_large vector_full
- gpu_preference:
    when: has_gpu
    prefer: inference_tasks
- cost_optimization:
    when: node_type == "free_tier" and load > 70%
    action: migrate_to_low_load_node

## Интеграция
- dynamic-tool-orchestrator (основной потребитель)
- resource-demand-evaluator
- load-aware-scheduler
- consent-orchestrator (перед применением)

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
- Описание назначения: Гибкий движок политик для динамического распределения инструментов. Позволяет задавать сложные правила: \"в development mode на всех бесплатных нодах выключить всё тяжелое\", \"на нодах с GPU приоритет отдавать inference\", \"при нагрузке > 80% переносить задачу\". Используется dynamic-tool-orchestrator.
