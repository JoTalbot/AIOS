---
name: context-refresh
description: Обновление и очистка контекста для предотвращения утечек памяти и устаревания данных.
---

# Context Refresh

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/context-refresh`

## Описание
Обновление и очистка контекста для предотвращения утечек памяти и устаревания данных.

## Цели
- Обновление контекста в памяти
- Очистка старого контекста
- Контроль утечек контекста
- Проверка freshness контекста

## Рутины

### `refresh_context.py`
```python
# Обновление контекста
# Функция: refresh_context(force=False)
```

### `cleanup_context.py**
```python
# Очистка контекста
# Функция: cleanup_context()
```

### `check_context_freshness.py**
```python
# Проверка свежести контекста
# Функция: check_context_freshness(timeout_minutes=30)
```

## Метрики
- `context_size_bytes`: Размер контекста (bytes)
- `context_freshness_seconds`: Свежесть контекста (сек)
- `context_leaks`: Количество утечек контекста
- `context_cleanup_count`: Количество очисток
- `refresh_frequency_seconds`: Частота обновления (сек)

## Пример использования
```bash
# Обновление контекста
python3 code/refresh_context.py

# Очистка контекста
python3 code/cleanup_context.py

# Проверка свежести
python3 code/check_context_freshness.py
```

## Векторный coverage
- ✅ Context refresh
- ✅ Context cleanup
- ✅ Context freshness monitoring
- ✅ Memory leak prevention

## Anti-patterns to fix
1. Stale context
2. Memory leaks from context
3. Context overflow
4. No context refresh
5. Too frequent context cleanup

## Best practices
- Refresh every 30 minutes
- Cleanup context after use
- Monitor context size
- Avoid context leaks
- Use context pooling

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
- Описание назначения: Обновление и очистка контекста для предотвращения утечек памяти и устаревания данных.
