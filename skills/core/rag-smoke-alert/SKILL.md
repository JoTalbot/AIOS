---
name: rag-smoke-alert
description: Smoke tests и alerts для RAG search для быстрого выявления проблем.
---

# RAG Smoke Alert

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/rag-smoke-alert`

## Описание
Smoke tests и alerts для RAG search для быстрого выявления проблем.

## Цели
- Run smoke tests для RAG
- Детектировать проблемы RAG
- Генерировать alerts
- Мonitoring RAG health

## Рутины

### `run_smoke_tests.py**
```python
# Запуск smoke tests
# Проверка RAG функциональности
```

### `detect_rag_problems.py**
```python
# Детектировать проблемы RAG
# Функция: detect_rag_problems()
```

### `generate_alerts.py**
```python
# Генерировать alerts
# Функция: generate_alerts()
```

## Метрики
- `smoke_tests_passed`: Прошло smoke tests
- `issues_detected`: Найдено проблем
- `alerts_generated`: Alerts создано
- `rag_health_score`: Здоровье RAG (%)
- `test_coverage_pct`: Coverage тестов (%)

## Пример использования
```bash
# Smoke tests
python3 code/run_smoke_tests.py

# Детекция проблем
python3 code/detect_rag_problems.py

# Alerts
python3 code/generate_alerts.py
```

## Векторный coverage
- ✅ Smoke tests
- ✅ Problem detection
- ✅ Alert generation
- ✅ Health monitoring

## Anti-patterns to fix
1. RAG broken
2. Smoke tests failing
3. No alerts
4. Hidden issues
5. Low test coverage

## Common issues
- Search failures
- Index issues
- Timeout errors
- Performance degradation

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
- Описание назначения: Smoke tests и alerts для RAG search для быстрого выявления проблем.
