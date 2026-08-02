---
name: voice-audio-graph
description: Аудит и мониторинг voice audio graph для проверки распознавания голоса.
---

# Voice Audio Graph

**Вектор**: autoheal
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/voice-audio-graph`

## Описание
Аудит и мониторинг voice audio graph для проверки распознавания голоса.

## Цели
- Мониторинг voice audio graph
- Детектировать проблемы с audio graph
- Проверка voice recognition
- Оптимизация audio processing

## Рутины

### `audit_audio_graph.py**
```python
# Аудит audio graph
# Проверка voice recognition
```

### `detect_audio_problems.py**
```python
# Детектировать проблемы audio
# Функция: detect_audio_problems()
```

### `optimize_audio_processing.py**
```python
# Оптимизировать audio processing
# Функция: optimize_audio_processing()
```

## Метрики
- `audio_graph_status`: Статус audio graph
- `voice_recognition_accuracy`: Точность распознавания (%)
- `audio_errors`: Количество ошибок аудио
- `processing_time_ms`: Время обработки (ms)
- `graph_health_score`: Здоровье графа (%)

## Пример использования
```bash
# Аудит audio graph
python3 code/audit_audio_graph.py

# Детекция проблем
python3 code/detect_audio_problems.py

# Оптимизация
python3 code/optimize_audio_processing.py
```

## Векторный coverage
- ✅ Audio graph audit
- ✅ Voice recognition monitoring
- ✅ Problem detection
- ✅ Optimization

## Anti-patterns to fix
1. Audio graph broken
2. Voice recognition failed
3. Noisy audio processing
4. Audio errors
5. Slow audio processing

## Common issues
- Audio not recognized
- Voice processing errors
- Noisy graph
- Graph inconsistencies

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
- Описание назначения: Аудит и мониторинг voice audio graph для проверки распознавания голоса.
