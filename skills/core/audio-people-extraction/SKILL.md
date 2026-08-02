---
name: audio-people-extraction
description: Извлечение people graph из аудио для голосового распознавания.
---

# Audio People Extraction

**Вектор**: autoheal
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/audio-people-extraction`

## Описание
Извлечение people graph из аудио для голосового распознавания.

## Цели
- Извлечь people graph из аудио
- Мониторинг people extraction
- Детектировать проблемы extraction
- Оптимизация extraction accuracy

## Рутины

### `extract_people_graph.py**
```python
# Извлечь people graph
# Функция: extract_people_graph(audio_file)
```

### `monitor_extraction.py**
```python
# Мониторинг extraction
# Функция: monitor_extraction()
```

### `optimize_extraction.py**
```python
# Оптимизировать extraction
# Функция: optimize_extraction()
```

## Метрики
- `people_extracted`: Extracted people count
- `extraction_accuracy`: Точность extraction (%)
- `audio_errors`: Количество ошибок аудио
- `extraction_time_ms`: Время extraction (ms)
- `graph_quality_score`: Качество графа (%)

## Пример использования
```bash
# Извлечь people graph
python3 code/extract_people_graph.py

# Мониторинг
python3 code/monitor_extraction.py

# Оптимизация
python3 code/optimize_extraction.py
```

## Векторный coverage
- ✅ People graph extraction
- ✅ Monitoring
- ✅ Optimization
- ✅ Quality checks

## Anti-patterns to fix
1. People extraction failed
2. Low extraction accuracy
3. Noisy extraction
4. Graph inconsistencies
5. Extraction timeouts

## Known issues
- Noisy STT conversion
- People graph too noisy
- Extraction failures
- Graph quality issues

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
- Описание назначения: Извлечение people graph из аудио для голосового распознавания.
