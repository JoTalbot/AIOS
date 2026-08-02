---
name: roadmap-1000-alerts
description: Управление alerts/security/voice/disk для roadmap 1000.
---

# Roadmap 1000 Alerts

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/roadmap-1000-alerts`

## Описание
Управление alerts/security/voice/disk для roadmap 1000.

## Цели
- Управлять alerts
- Управлять security
- Управлять voice
- Управлять disk

## Рутины

### `manage_alerts.py**
```python
# Управлять alerts
# Функция: manage_alerts(action)
```

### `manage_security.py**
```python
# Управлять security
# Функция: manage_security(action)
```

### `manage_voice.py**
```python
# Управлять voice
# Функция: manage_voice(action)
```

### `manage_disk.py**
```python
# Управлять disk
# Функция: manage_disk(action)
```

## Метрики
- `alerts_active`: Активные alerts
- `security_issues`: Проблемы security
- `voice_available`: Voice доступен
- `disk_usage_percent`: Использование диска (%)
- `status`: Общий статус

## Пример использования
```bash
# Управлять alerts
python3 code/manage_alerts.py

# Управлять security
python3 code/manage_security.py

# Управлять voice
python3 code/manage_voice.py

# Управлять disk
python3 code/manage_disk.py
```

## Векторный coverage
- ✅ Alert management
- ✅ Security management
- ✅ Voice management
- ✅ Disk management

## Anti-patterns to fix
1. Too many alerts
2. Security issues
3. Voice problems
4. Disk full
5. No management

## Common issues
- Alerts flooding
- Security vulnerabilities
- Voice failures
- Disk quota exceeded
- No monitoring

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
- Описание назначения: Управление alerts/security/voice/disk для roadmap 1000.
