---
name: whisper-transcribe-health
description: Проверка здоровья/исправности Whisper STT и диаризации для выявления проблем с аудио-распознаванием.
---

# Whisper Transcribe Health Check

**Вектор**: autoheal
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/whisper-transcribe-health`

## Описание
Проверка здоровья/исправности Whisper STT и диаризации для выявления проблем с аудио-распознаванием.

## Цели
- Мониторинг Whisper STT работоспособности
- Проверка диаризации (speaker mapping)
- Детекция проблем с long audio
- Проверка chunked STT

## Рутины

### `check_stt_health.py`
```python
# Проверка STT health
# Тест на простое аудио
```

### `check_diarization.py`
```python
# Проверка диаризации
# Функция: check_speaker_mapping(audio_file)
```

### `test_chunked_processing.py**
```python
# Тест chunked STT
# Функция: test_chunked_processing(audio_file)
```

## Метрики
- `stt_available`: STT доступен
- `diarization_available`: Диаризация доступна
- `chunked_stt_success`: Chunked STT успешен
- `audio_errors`: Количество ошибок аудио
- `processing_time_ms`: Время обработки (ms)

## Пример использования
```bash
# Базовая проверка
python3 code/check_stt_health.py

# Проверка диаризации
python3 code/check_diarization.py

# Тест chunked
python3 code/test_chunked_processing.py
```

## Векторный coverage
- ✅ Whisper STT health check
- ✅ Speaker diarization verification
- ✅ Chunked STT testing
- ✅ Audio processing health

## Anti-patterns to fix
1. STT failures
2. Missing speaker mapping
3. Long audio processing errors
4. Chunked STT issues
5. Noisy STT conversion errors

## Known issues
- Long ambient recordings fail
- Speaker mapping noisy
- Chunked STT stability issues

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
- Описание назначения: Проверка здоровья/исправности Whisper STT и диаризации для выявления проблем с аудио-распознаванием.
