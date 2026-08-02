---
name: security-audit
description: Аудит безопасности для выявления уязвимостей, небезопасных паттернов и проблем с конфиденциальностью.
---

# Security Audit

**Вектор**: memory
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/security-audit`

## Описание
Аудит безопасности для выявления уязвимостей, небезопасных паттернов и проблем с конфиденциальностью.

## Цели
- Детекция уязвимостей безопасности
- Проверка конфиденциальности данных
- Аудит доступа и прав
- Выявление insecure patterns

## Рутины

### `audit_vulnerabilities.py`
```python
# Аудит уязвимостей
# Использует security scanning tools
```

### `check_privileges.py**
```python
# Проверка прав доступа
# Функция: check_file_permissions()
```

### `detect_secrets.py**
```python
# Детекция секретов
# Функция: detect_secrets(file_path)
```

## Метрики
- `vulnerabilities_found`: Найдено уязвимостей
- `secrets_detected`: Найдено секретов
- `permissions_issues`: Проблем с правами
- `audit_score`: Оценка безопасности
- `security_level`: Уровень безопасности

## Пример использования
```bash
# Аудит уязвимостей
python3 code/audit_vulnerabilities.py

# Проверка прав
python3 code/check_privileges.py

# Детекция секретов
python3 code/detect_secrets.py
```

## Векторный coverage
- ✅ Vulnerability detection
- ✅ Privilege audit
- ✅ Secrets detection
- ✅ Security scoring

## Anti-patterns to fix
1. Hardcoded secrets
2. Weak permissions
3. Unused access rights
4. Outdated dependencies
5. Security misconfigurations

## Critical vulnerabilities
- SQL injection
- XSS
- CSRF
- Authentication bypass
- Sensitive data exposure

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
- Описание назначения: Аудит безопасности для выявления уязвимостей, небезопасных паттернов и проблем с конфиденциальностью.
