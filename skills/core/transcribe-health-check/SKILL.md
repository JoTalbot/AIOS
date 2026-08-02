---
name: transcribe-health-check
description: Проверка здоровья/исправности Transcribe и Whisper для аудио-распознавания.
---

# Transcribe Health Check

**Вектор**: autoheal
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/transcribe-health-check`

## Описание
Проверка здоровья/исправности Transcribe и Whisper для аудио-распознавания.

## Цели
- Проверка Transcribe health
- Проверка Whisper STT работоспособности
- Мониторинг STT failures
- Проверка audio processing

## Рутины

### `check_transcribe_health.py**
```python
# Проверить Transcribe health
# Функция: check_transcribe_health()
```

### `check_whisper_health.py**
```python
# Проверить Whisper health
# Функция: check_whisper_health()
```

### `detect_stt_failures.py**
```python
# Детектировать STT failures
# Функция: detect_stt_failures()
```

## Метрики
- `transcribe_available`: Transcribe доступен
- `whisper_available`: Whisper доступен
- `stt_errors`: Количество ошибок STT
- `audio_processing_errors`: Количество ошибок обработки
- `health_score`: Оценка здоровья (%)

## Пример использования
```bash
# Проверить Transcribe
python3 code/check_transcribe_health.py

# Проверить Whisper
python3 code/check_whisper_health.py

# Детектировать failures
python3 code/detect_stt_failures.py
```

## Векторный coverage
- ✅ Transcribe health check
- ✅ Whisper STT check
- ✅ Failure detection
- ✅ Health monitoring

## Anti-patterns to fix
1. STT failures
2. Whisper not working
3. Transcribe issues
4. Audio processing errors
5. No health checks

## Common issues
- Transcribe not working
- Whisper errors
- STT timeouts
- No health monitoring

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
- Описание назначения: Проверка здоровья/исправности Transcribe и Whisper для аудио-распознавания.
