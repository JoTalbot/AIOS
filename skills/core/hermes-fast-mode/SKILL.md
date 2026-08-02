---
name: hermes-fast-mode
description: Настройка fast mode для Hermes для ускорения работы.
---

# Hermes Fast Mode

**Вектор**: swarm
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/hermes-fast-mode`

## Описание
Настройка fast mode для Hermes для ускорения работы.

## Цели
- Включить Hermes fast mode
- Оптимизировать Hermes performance
- Мониторинг fast mode status
- Детектировать проблемы с fast mode

## Рутины

### `enable_fast_mode.py**
```python
# Включить fast mode
# Функция: enable_fast_mode()
```

### `optimize_hermes.py**
```python
# Оптимизировать Hermes
# Функция: optimize_hermes()
```

### `monitor_fast_mode.py**
```python
# Мониторинг fast mode
# Функция: monitor_fast_mode()
```

## Метрики
- `fast_mode_active`: Fast mode активен
- `performance_improvement_pct`: Улучшение производительности (%)
- `response_time_ms`: Время ответа (ms)
- `error_rate`: Процент ошибок
- `hermes_health`: Здоровье Hermes

## Пример использования
```bash
# Включить fast mode
python3 code/enable_fast_mode.py

# Оптимизировать Hermes
python3 code/optimize_hermes.py

# Мониторинг fast mode
python3 code/monitor_fast_mode.py
```

## Векторный coverage
- ✅ Fast mode enable/disable
- ✅ Hermes optimization
- ✅ Performance monitoring
- ✅ Health checks

## Anti-patterns to fix
1. Hermes slow response
2. Fast mode not working
3. Performance degradation
4. Errors in fast mode
5. No Hermes monitoring

## Known issues
- Hermes 404 errors
- Slow responses
- Memory issues
- No fast mode toggle

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
- Описание назначения: Настройка fast mode для Hermes для ускорения работы.
