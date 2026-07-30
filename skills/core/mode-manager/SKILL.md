---
name: mode-manager
description: Централизованное управление глобальными режимами работы системы (development, production, minimal, maintenance, night, high-load). Переключает desired-state и триггерит dynamic-tool-orchestrator.
---
# Mode Manager

## Поддерживаемые режимы
- development (то, что просил пользователь)
- production
- minimal
- maintenance
- night / low-activity
- high-load / peak

## Команды
- switch_mode("development")
- get_current_mode()
- list_modes()

## Что происходит при переключении
1. Устанавливает tool-desired-state для нового режима
2. Вызывает dynamic-tool-orchestrator.reconcile()
3. Логирует + уведомляет
4. Требует consent для production-критичных изменений

## Интеграция
- development-mode-guard
- dynamic-tool-orchestrator
- tool-desired-state
- consent-orchestrator

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
- Описание назначения: Централизованное управление глобальными режимами работы системы (development, production, minimal, maintenance, night, high-load). Переключает desired-state и триггерит dynamic-tool-orchestrator.
