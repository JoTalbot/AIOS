---
name: memory-storage-audit
description: Аудит памяти и хранилища для выявления утечек памяти и неэффективного использования ресурсов.
---

# Memory Storage Audit

**Вектор**: memory
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/memory-storage-audit`

## Описание
Аудит памяти и хранилища для выявления утечек памяти и неэффективного использования ресурсов.

## Цели
- Детекция memory leaks
- Мониторинг использования памяти
- Проверка storage runbook compliance
- Оптимизация memory footprint

## Рутины

### `audit_memory.py`
```python
# Основная функция для аудита памяти
# Использует ps, free, vmstat для мониторинга
```

### `detect_leaks.py**
```python
# Детекция memory leaks
# Функция: detect_memory_leaks(sample_count=100)
```

### `check_storage.py**
```python
# Проверка storage compliance
# Функция: check_storage_limits()
```

## Метрики
- `memory_used_mb`: Использовано памяти (MB)
- `memory_available_mb`: Доступно памяти (MB)
- `memory_leaks_detected`: Количество утечек
- `storage_usage_percent`: Использование хранилища (%)
- `leak_pattern`: Выявленный паттерн утечки

## Пример использования
```bash
# Базовый аудит памяти
python3 code/audit_memory.py

# Детекция утечек
python3 code/detect_leaks.py

# Проверка storage
python3 code/check_storage.py
```

## Векторный coverage
- ✅ Memory leak detection
- ✅ Memory usage monitoring
- ✅ Storage audit
- ✅ Memory footprint optimization

## Anti-patterns to fix
1. Memory leaks (unreleased objects)
2. High memory usage (>80%)
3. Memory fragmentation
4. Storage limit violations
5. Caching issues

## Storage runbook compliance
- Cache size limits: checked
- Memory thresholds: monitored
- Storage cleanup: automated
- Backup compliance: verified

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
- Описание назначения: Аудит памяти и хранилища для выявления утечек памяти и неэффективного использования ресурсов.
