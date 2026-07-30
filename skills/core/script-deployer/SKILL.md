---
name: script-deployer
description: Универсальный инструмент для динамической установки, удаления, запуска и остановки скриптов/сервисов/моделей как локально, так и удалённо по решению оркестратора.
---
# Script Deployer

## Описание

Этот скил предназначен для...

## Команды
- deploy(tool_name, version, target_nodes)
- undeploy(tool_name, target_nodes)
- start(tool_name, target_nodes)
- stop(tool_name, target_nodes)
- status(tool_name)

## Поддерживаемые типы инструментов
- Python скрипты
- systemd units
- Docker containers
- Ollama / Whisper / другие модели
- Octopus skills (через loader)
- Пользовательские бинарники

## Безопасность
- Обязательно проходит через consent-orchestrator
- Проверка цифровой подписи (если есть)
- Откат при ошибке
- Логирование всех изменений

## Пример использования динамическим оркестратором
"В development mode: останови все модели на всех нодах кроме 2 лёгких"

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
- Описание назначения: Универсальный инструмент для динамической установки, удаления, запуска и остановки скриптов/сервисов/моделей как локально, так и удалённо по решению оркестратора.
