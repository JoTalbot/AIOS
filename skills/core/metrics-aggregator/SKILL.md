---
name: metrics-aggregator
description: Агрегирование и сбор метрик из различных источников для создания единого view производительности.
---

# Metrics Aggregator

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/metrics-aggregator`

## Описание
Агрегирование и сбор метрик из различных источников для создания единого view производительности.

## Цели
- Собирать метрики из разных источников
- Агрегировать метрики в единый view
- Детектировать аномалии в агрегированных метриках
- Поддержка real-time и batch метрик

## Рутины

### `aggregate_metrics.py`
```python
# Агрегирование метрик
# Функция: aggregate_metrics(sources, refresh_rate)
```

### `collect_metrics.py**
```python
# Сбор метрик
# Функция: collect_metrics(sources)
```

### `build_dashboard.py**
```python
# Построение dashboard
# Функция: build_dashboard(metric_types)
```

## Метрики
- `total_metrics_collected`: Всего собрано метрик
- `aggregation_latency_ms`: Задержка агрегации (ms)
- `anomalies_detected`: Найдено аномалий
- `metrics_sources`: Количество источников метрик
- `aggregation_success_rate`: Успешность агрегации (%)

## Пример использования
```bash
# Агрегирование метрик
python3 code/aggregate_metrics.py

# Сбор метрик
python3 code/collect_metrics.py

# Построение dashboard
python3 code/build_dashboard.py
```

## Векторный coverage
- ✅ Metrics collection
- ✅ Metrics aggregation
- ✅ Real-time aggregation
- ✅ Dashboard building

## Anti-patterns to fix
1. Metrics from glob (deprecated)
2. Incomplete metric collection
3. Missing metrics aggregation
4. No anomaly detection
5. Slow aggregation

## Common issues
- Too many metrics sources
- Missing metric types
- Aggregation lag
- Data inconsistency
- No metric validation

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
- Описание назначения: Агрегирование и сбор метрик из различных источников для создания единого view производительности.
