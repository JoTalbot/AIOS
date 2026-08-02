---
name: chunked-audio-mapping
description: Chunked mapping для long audio для улучшения STT.
---

# Chunked Audio Mapping

**Вектор**: autoheal
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/chunked-audio-mapping`

## Описание
Chunked mapping для long audio для улучшения STT.

## Цели
- Chunk аудио для long recordings
- Map speakers в chunks
- Обеспечить стабильность STT
- Оптимизировать audio processing

## Рутины

### `map_chunked_audio.py**
```python
# Map chunked audio
# Функция: map_chunked_audio(audio_file)
```

### `stabilize_stt.py**
```python
# Stabilize STT
# Функция: stabilize_stt(audio_file)
```

### `optimize_chunks.py**
```python
# Оптимизировать chunks
# Функция: optimize_chunks()
```

## Метрики
- `chunks_created`: Created chunks count
- `speaker_mapping_accuracy`: Точность mapping (%)
- `stt_stability`: Стабильность STT
- `audio_processing_time_ms`: Время обработки (ms)
- `stt_errors`: Количество ошибок STT

## Пример использования
```bash
# Map chunked audio
python3 code/map_chunked_audio.py

# Stabilize STT
python3 code/stabilize_stt.py

# Оптимизация
python3 code/optimize_chunks.py
```

## Векторный coverage
- ✅ Chunked audio mapping
- ✅ STT stability
- ✅ Speaker mapping
- ✅ Optimization

## Anti-patterns to fix
1. Chunked STT unstable
2. Speaker mapping issues
3. Noisy mapping
4. STT errors
5. Long audio failures

## Known issues
- 20min STT stability issues
- Noisy STT conversion
- Chunked audio processing errors
- Mapping inconsistencies

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
- Описание назначения: Chunked mapping для long audio для улучшения STT.
