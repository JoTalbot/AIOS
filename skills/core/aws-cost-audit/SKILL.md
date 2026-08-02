---
name: aws-cost-audit
description: Автоматический аудит AWS расходов для выявления затрат и оптимизации возможностей.
---

# AWS Cost Audit

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/aws-cost-audit`

## Описание
Автоматический аудит AWS расходов для выявления затрат и оптимизации возможностей.

## Цели
- Мониторинг AWS расходов
- Выявление неэффективных ресурсов
- Оптимизация стоимости
- Детекция аномалий в тратах

## Рутины

### `audit_costs.py`
```python
# Основная функция для аудита AWS расходов
# Использует AWS CLI и CloudWatch для сбора метрик
```

### `find_inefficiencies.py`
```python
# Поиск неэффективных ресурсов
# Функция: find_inefficient_ec2_instances(region)
```

### `detect_anomalies.py`
```python
# Детекция аномалий в тратах
# Функция: detect_cost_anomalies(start_date, end_date)
```

## Метрики
- `total_cost`: Общие расходы
- `monthly_avg_cost`: Среднемесячные расходы
- `cost_change_percent`: Изменение расходов (%)
- `inefficient_resources`: Количество неэффективных ресурсов
- `optimization_potential`: Потенциальная экономия ($)

## Пример использования
```bash
# Базовый аудит
python3 code/audit_costs.py --region us-east-1

# Сравнение с прошлым периодом
python3 code/audit_costs.py --compare last_month

# Генерация отчета
python3 code/audit_costs.py --report report.json
```

## Векторный coverage
- ✅ Cost monitoring
- ✅ Resource inefficiency detection
- ✅ Cost anomaly detection
- ✅ Optimization recommendations

## Anti-patterns to fix
1. Unattached EBS volumes
2. Stopped EC2 instances
3. Unused S3 buckets
4. Oversized instances
5. Reserved vs on-demand mismatch

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
- Описание назначения: Автоматический аудит AWS расходов для выявления затрат и оптимизации возможностей.
