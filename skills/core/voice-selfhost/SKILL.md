---
name: voice-selfhost
description: Настройка и мониторинг self-hosted голосовых сервисов для замены cloud решений (Google Voice, Notion automation).
---

# Voice Self-Host

**Вектор**: swarm
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/voice-selfhost`

## Описание
Настройка и мониторинг self-hosted голосовых сервисов для замены cloud решений (Google Voice, Notion automation).

## Цели
- Мониторинг self-hosted voice
- Проверка доступности voice services
- Детекция проблем с голосовыми API
- Оптимизация voice latency

## Рутины

### `check_voice_service.py**
```python
# Проверка voice service
# Тестирование голосового API
```

### `monitor_voice_health.py**
```python
# Мониторинг здоровья voice
# Функция: monitor_voice_health()
```

### `detect_voice_failures.py**
```python
# Детекция отказов voice
# Функция: detect_voice_failures()
```

## Метрики
- `voice_available`: Voice доступен
- `voice_latency_ms`: Задержка voice (ms)
- `voice_failures`: Количество отказов
- `voice_availability_pct`: Доступность voice (%)
- `voice_downtime_seconds`: Downtime voice (сек)

## Пример использования
```bash
# Проверка voice service
python3 code/check_voice_service.py

# Мониторинг voice
python3 code/monitor_voice_health.py

# Детекция отказов
python3 code/detect_voice_failures.py
```

## Векторный coverage
- ✅ Voice service health
- ✅ Voice availability monitoring
- ✅ Voice failure detection
- ✅ Voice latency optimization

## Anti-patterns to fix
1. Voice service unavailable
2. High voice latency
3. Voice API failures
4. Voice quota exceeded
5. No voice fallback

## Known issues
- Voice selfhost unstable
- Cloud voice replacement needed
- Voice API rate limits
- Voice quality issues

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
- Описание назначения: Настройка и мониторинг self-hosted голосовых сервисов для замены cloud решений (Google Voice, Notion automation).
