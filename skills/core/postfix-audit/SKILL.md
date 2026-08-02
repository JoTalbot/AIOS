---
name: postfix-audit
description: Аудит и мониторинг Postfix mail server для выявления проблем с почтой.
---

# Postfix Audit

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/postfix-audit`

## Описание
Аудит и мониторинг Postfix mail server для выявления проблем с почтой.

## Цели
- Проверка конфигурации Postfix
- Детекция проблем с доставкой почты
- Мониторинг queue status
- Проверка на blacklists

## Рутины

### `audit_postfix.py**
```python
# Аудит Postfix конфигурации
# Проверка основных параметров
```

### `check_mail_queue.py**
```python
# Проверка почтовой очереди
# Функция: check_mail_queue()
```

### `monitor_delivery.py**
```python
# Мониторинг доставки почты
# Функция: monitor_delivery()
```

## Метрики
- `queue_count`: Количество сообщений в очереди
- `bounced_count`: Количество bounced сообщений
- `delivery_rate`: Процент успешной доставки (%)
- `spam_rate`: Процент спама (%)
- `config_issues`: Проблемы с конфигурацией

## Пример использования
```bash
# Аудит Postfix
python3 code/audit_postfix.py

# Проверка очереди
python3 code/check_mail_queue.py

# Мониторинг доставки
python3 code/monitor_delivery.py
```

## Векторный coverage
- ✅ Postfix audit
- ✅ Mail queue monitoring
- ✅ Delivery monitoring
- ✅ Spam detection

## Anti-patterns to fix
1. Mail queue overflow
2. High bounce rate
3. Misconfigured Postfix
4. Blacklisted IPs
5. No mail delivery

## Common issues
- Queue too large
- Connection timeouts
- Spam filtering issues
- Config syntax errors
- DNS issues

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
- Описание назначения: Аудит и мониторинг Postfix mail server для выявления проблем с почтой.
