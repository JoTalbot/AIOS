---
name: storage-optimization
description: Оптимизация storage и очистка неиспользуемых данных для освобождения места.
---

# Storage Optimization

**Вектор**: memory
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/storage-optimization`

## Описание
Оптимизация storage и очистка неиспользуемых данных для освобождения места.

## Цели
- Выявление неиспользуемых файлов
- Оптимизация размера данных
- Очистка кэша
- Проверка compliance с quota

## Рутины

### `find_unused_files.py`
```python
# Поиск неиспользуемых файлов
# Функция: find_unused_files(directory, days=30)
```

### `optimize_storage.py**
```python
# Оптимизация storage
# Функция: optimize_storage(dry_run=True)
```

### `check_quota.py**
```python
# Проверка quota
# Функция: check_storage_quota()
```

## Метрики
- `unused_files_count`: Количество неиспользуемых файлов
- `storage_freed_mb`: Освобождено места (MB)
- `disk_usage_percent`: Использование диска (%)
- `quota_compliance`: Соответствие квоте
- `optimization_potential_mb`: Потенциал оптимизации (MB)

## Пример использования
```bash
# Поиск неиспользуемых файлов
python3 code/find_unused_files.py

# Оптимизация storage
python3 code/optimize_storage.py

# Проверка quota
python3 code/check_quota.py
```

## Векторный coverage
- ✅ Unused file detection
- ✅ Storage optimization
- ✅ Quota compliance
- ✅ Cache cleanup

## Anti-patterns to fix
1. Too many unused files
2. Storage quota exceeded
3. Large cache files
4. Redundant data
5. Unoptimized storage structures

## Optimization techniques
- Delete unused files
- Compress old data
- Optimize database storage
- Clear caches
- Archive old logs

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
- Описание назначения: Оптимизация storage и очистка неиспользуемых данных для освобождения места.
