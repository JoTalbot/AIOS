---
name: context-read-arena
description: Аудит контекстного чтения для arena agents и проверки согласованности контекста между узлами.
---

# Context Read Arena

**Вектор**: swarm
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/context-read-arena`

## Описание
Аудит контекстного чтения для arena agents и проверки согласованности контекста между узлами.

## Цели
- Проверка контекстного чтения для arena
- Мониторинг согласованности контекста
- Детекция рассинхронизации контекста
- Проверка arena agent capabilities

## Рутины

### `read_arena_context.py`
```python
# Чтение контекста arena
# Функция: read_arena_context(agent_id)
```

### `check_context_consistency.py**
```python
# Проверка согласованности контекста
# Функция: check_context_consistency()
```

### `detect_context_lag.py**
```python
# Детекция рассинхронизации контекста
# Функция: detect_context_lag()
```

## Метрики
- `context_read_speed_ms`: Скорость чтения контекста (ms)
- `context_consistency_pct`: Процент согласованности контекста
- `context_nodes_count`: Количество узлов с контекстом
- `context_lag_nodes`: Количество узлов с отставанием
- `context_freshness_seconds`: Свежность контекста (сек)

## Пример использования
```bash
# Базовое чтение контекста
python3 code/read_arena_context.py

# Проверка согласованности
python3 code/check_context_consistency.py

# Детекция отставания
python3 code/detect_context_lag.py
```

## Векторный coverage
- ✅ Arena context reading
- ✅ Context consistency monitoring
- ✅ Context lag detection
- ✅ Node context availability

## Anti-patterns to fix
1. Context desynchronization
2. Slow context reads
3. Missing context nodes
4. Context staleness
5. Context conflicts

## Arena requirements
- Context must be synced across all nodes
- Context read speed < 100ms
- Context freshness < 1 minute
- No context conflicts

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
- Описание назначения: Аудит контекстного чтения для arena agents и проверки согласованности контекста между узлами.
