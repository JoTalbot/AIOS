---
name: multi-sync-monitor
description: Мониторинг multi-master active-active синхронизации для выявления рассинхронизаций.
---

# Multi-Sync Monitor

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/multi-sync-monitor`

## Описание
Мониторинг multi-master active-active синхронизации для выявления рассинхронизаций.

## Цели
- Мониторинг multi-master синхронизации
- Детекция рассинхронизаций
- Проверка sync health
- Автоматическое обнаружение проблем

## Рутины

### `monitor_sync.py**
```python
# Мониторинг синхронизации
# Проверка статус sync
```

### `detect_lag.py**
```python
# Детекция рассинхронизации
# Функция: detect_lag()
```

### `check_sync_health.py**
```python
# Проверка здоровья синхронизации
# Функция: check_sync_health()
```

## Метрики
- `sync_nodes_count`: Количество sync узлов
- `sync_lag_seconds`: Отставание синхронизации (сек)
- `sync_failures`: Количество failed sync
- `sync_success_rate`: Успешность синхронизации (%)
- `nodes_consistent`: Количество согласованных узлов

## Пример использования
```bash
# Мониторинг синхронизации
python3 code/monitor_sync.py

# Детекция рассинхронизации
python3 code/detect_lag.py

# Проверка здоровья
python3 code/check_sync_health.py
```

## Векторный coverage
- ✅ Multi-master sync monitoring
- ✅ Sync lag detection
- ✅ Health checks
- ✅ Consistency verification

## Anti-patterns to fix
1. Sync desynchronization
2. High sync lag
3. Failed sync attempts
4. Node inconsistency
5. No sync monitoring

## Common issues
- Network partition
- Node failures
- Configuration conflicts
- Sync conflicts
- Deadlocks

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
- Описание назначения: Мониторинг multi-master active-active синхронизации для выявления рассинхронизаций.
