---
name: resource-demand-evaluator
description: Оценивает текущую необходимость тех или иных процессов/инструментов исходя из режима работы проекта, нагрузки пользователей и состояния системы.
---
# Resource Demand Evaluator

## Описание

Этот скил предназначен для...

## Факторы оценки
- Текущий "режим" проекта (development / production / maintenance / testing)
- Активность пользователей (TG bot, API запросы)
- Плановые задачи (chaos tests, eternal snapshots, reproduction)
- Доступные ресурсы на free-tier нодах

## Примеры решений
- "Сейчас идёт активная разработка" → demand для тяжёлых моделей = низкий
- "Запущен production voice service" → demand для whisper + vector = высокий
- "Ночь + низкая активность" → можно выключить часть нод/процессов

## Выход
Возвращает demand-map:
{
  "whisper-worker": "high",
  "ollama-large": "none",
  "vector-search": "medium",
  ...
}

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
- Описание назначения: Оценивает текущую необходимость тех или иных процессов/инструментов исходя из режима работы проекта, нагрузки пользователей и состояния системы.
