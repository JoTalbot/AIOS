---
name: postgresql-performance-audit
description: Аудит производительности PostgreSQL для выявления проблем и оптимизации базы данных.
---

# PostgreSQL Performance Audit

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/postgresql-performance-audit`

## Описание
Аудит производительности PostgreSQL для выявления проблем и оптимизации базы данных.

## Цели
- Мониторинг query performance
- Детекция slow queries
- Оптимизация индексов
- Выявление блокировок
- Проверка autovacuum compliance

## Рутины

### `audit_performance.py`
```python
# Основная функция для аудита производительности
# Использует EXPLAIN ANALYZE и pg_stat_statements
```

### `detect_slow_queries.py`
```python
# Детекция медленных запросов
# Функция: detect_slow_queries(threshold_seconds=2.0)
```

### `check_indexes.py**
```python
# Проверка индексов
# Функция: analyze_index_usage()
```

## Метрики
- `slow_queries_count`: Количество медленных запросов
- `avg_query_time_ms`: Среднее время запроса (ms)
- `index_usage_ratio`: Процент использования индексов
- `blocking_queries`: Количество заблокированных запросов
- `autovacuum_rate`: Скорость autovacuum

## Пример использования
```bash
# Базовый аудит
python3 code/audit_performance.py

# Детекция медленных запросов
python3 code/detect_slow_queries.py --threshold 2.0

# Проверка индексов
python3 code/check_indexes.py
```

## Векторный coverage
- ✅ Query performance monitoring
- ✅ Slow query detection
- ✅ Index analysis
- ✅ Lock detection

## Anti-patterns to fix
1. Slow queries (>2s)
2. Unused indexes
3. Missing indexes
4. Blocking queries
5. Autovacuum issues

## Common issues
- Missing indexes
- Inefficient queries
- Table bloat
- Connection leaks
- Transaction bloat

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
- Описание назначения: Аудит производительности PostgreSQL для выявления проблем и оптимизации базы данных.
