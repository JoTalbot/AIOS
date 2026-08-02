---
name: metrics-alerts
description: Мониторинг метрик и предупреждение/alerts для выявления проблем с производительностью и ресурсами.
---

# Metrics Alerts

**Вектор**: memory
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/metrics-alerts`

## Описание
Мониторинг метрик и предупреждение/alerts для выявления проблем с производительностью и ресурсами.

## Цели
- Мониторинг ключевых метрик
- Детекция аномалий в метриках
- Генерация alerts
- Проверка alert compliance

## Рутины

### `monitor_metrics.py`
```python
# Основная функция для мониторинга метрик
# Использует Prometheus, Grafana, или custom metrics
```

### `detect_anomalies.py**
```python
# Детекция аномалий в метриках
# Функция: detect_anomalies(threshold_std=3.0)
```

### `generate_alerts.py**
```python
# Генерация alerts
# Функция: generate_alerts(metric_type, severity)
```

## Метрики
- `cpu_usage_percent`: Использование CPU (%)
- `memory_usage_percent`: Использование памяти (%)
- `disk_usage_percent`: Использование диска (%)
- `network_incoming_mb/s`: Входящий трафик (MB/s)
- `network_outgoing_mb/s`: Исходящий трафик (MB/s)
- `alerts_generated`: Количество alerts

## Пример использования
```bash
# Базовый мониторинг
python3 code/monitor_metrics.py

# Детекция аномалий
python3 code/detect_anomalies.py --threshold 3.0

# Генерация alerts
python3 code/generate_alerts.py
```

## Векторный coverage
- ✅ Metrics monitoring
- ✅ Anomaly detection
- ✅ Alert generation
- ✅ Alert compliance

## Anti-patterns to fix
1. High CPU (>80%)
2. Memory leaks (>90%)
3. Disk full (>95%)
4. Network anomalies
5. No metrics alerts

## Alert levels
- Warning: >70% usage
- Critical: >90% usage
- Fatal: >95% usage or errors

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
- Описание назначения: Мониторинг метрик и предупреждение/alerts для выявления проблем с производительностью и ресурсами.
