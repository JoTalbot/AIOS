---
name: roadmap-1000-disk-green
description: Управление disk, JuiceFS, Garage и bind-mount memory pool.
---

# Roadmap 1000 Disk Green

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/roadmap-1000-disk-green`

## Описание
Управление disk, JuiceFS, Garage и bind-mount memory pool.

## Цели
- Управлять disk
- Управлять JuiceFS
- Управлять Garage
- Управлять bind-mount memory pool

## Рутины

### `manage_disk.py**
```python
# Управлять disk
# Функция: manage_disk(action)
```

### `manage_juicefs.py**
```python
# Управлять JuiceFS
# Функция: manage_juicefs(action)
```

### `manage_garage.py**
```python
# Управлять Garage
# Функция: manage_garage(action)
```

### `manage_memory_pool.py**
```python
# Управлять bind-mount memory pool
# Функция: manage_memory_pool(action)
```

## Метрики
- `disk_usage_percent`: Использование диска (%)
- `juicefs_status`: Статус JuiceFS
- `garage_status`: Статус Garage
- `memory_pool_usage`: Использование memory pool (%)
- `disk_health`: Здоровье диска

## Пример использования
```bash
# Управлять disk
python3 code/manage_disk.py

# Управлять JuiceFS
python3 code/manage_juicefs.py

# Управлять Garage
python3 code/manage_garage.py

# Управлять memory pool
python3 code/manage_memory_pool.py
```

## Векторный coverage
- ✅ Disk management
- ✅ JuiceFS management
- ✅ Garage management
- ✅ Memory pool management

## Anti-patterns to fix
1. Disk full
2. JuiceFS issues
3. Garage issues
4. Memory pool full
5. No disk management

## Common issues
- Disk quota exceeded
- JuiceFS sync failures
- Garage not responding
- Memory pool overflow
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
- Описание назначения: Управление disk, JuiceFS, Garage и bind-mount memory pool.
