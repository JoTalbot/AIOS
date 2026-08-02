---
name: roadmap-1000-integration
description: Интеграция компонентов для roadmap 1000.
---

# Roadmap 1000 Integration

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/roadmap-1000-integration`

## Описание
Интеграция компонентов для roadmap 1000.

## Цели
- Интегрировать компоненты
- Проверять интеграцию
- Детектировать проблемы интеграции
- Упрощать интеграцию

## Рутины

### `check_integration.py**
```python
# Проверить интеграцию
# Функция: check_integration()
```

### `integrate_components.py**
```python
# Интегрировать компоненты
# Функция: integrate_components(components)
```

### `detect_integration_issues.py**
```python
# Детектировать проблемы интеграции
# Функция: detect_integration_issues()
```

## Метрики
- `components_integrated`: Интегрировано компонентов
- `integration_score`: Оценка интеграции (%)
- `issues_found`: Найдено проблем
- `integration_latency_ms`: Задержка интеграции (ms)
- `integration_status`: Статус интеграции

## Пример использования
```bash
# Проверить интеграцию
python3 code/check_integration.py

# Интегрировать компоненты
python3 code/integrate_components.py

# Детектировать проблемы
python3 code/detect_integration_issues.py
```

## Векторный coverage
- ✅ Integration check
- ✅ Component integration
- ✅ Issue detection
- ✅ Status monitoring

## Anti-patterns to fix
1. Integration broken
2. Component conflicts
3. Too many issues
4. No integration check
5. Slow integration

## Common issues
- Integration failures
- Component incompatibility
- Missing dependencies
- Integration conflicts
- No monitoring

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
- Описание назначения: Интеграция компонентов для roadmap 1000.
