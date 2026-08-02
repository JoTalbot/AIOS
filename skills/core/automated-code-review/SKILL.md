---
name: automated-code-review
description: Автоматический code review для выявления антипаттернов, дублирования кода, потенциальных багов и оптимизационных возможностей.
---

# Automated Code Review

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/automated-code-review`

## Описание
Автоматический code review для выявления антипаттернов, дублирования кода, потенциальных багов и оптимизационных возможностей.

## Цели
- Фиксация дублирования кода (>10%)
- Обнаружение deprecated кода
- Поиск устаревших зависимостей
- Выявление небезопасного кода
- Оптимизация производительности

## Рутины
### `review_file.py`
```python
# Основная функция для code review файла
# Использует static analysis паттерны для выявления проблем
```

### `detect_duplication.py`
```python
# Дублирование кода detection
# Функция: find_code_clones(file_path1, file_path2)
```

### `check_deprecated.py`
```python
# Deprecated code detection
# Функция: find_deprecated_patterns(file_path)
```

## Метрики
- `duplication_ratio`: Процент дублирования кода
- `deprecated_count`: Количество deprecated паттернов
- `security_issues`: Количество уязвимостей
- `optimization_opportunities`: Количество оптимизаций

## Пример использования
```bash
# Code review директории
python3 skills/core/automated-code-review/review_file.py --dir src/
python3 skills/core/automated-code-review/review_file.py --file src/api.py

# Генерация отчета
python3 skills/core/automated-code-review/review_file.py --report report.json
```

## Векторный coverage
- ✅ API quality (response schema validation)
- ✅ Code duplication detection
- ✅ Dead code detection
- ✅ Dependency updates
- ✅ Performance bottlenecks

## Anti-patterns to fix
1. Magic numbers (>3 без констант)
2. Hardcoded credentials
3. Nested conditionals (>3 уровня)
4. Long functions (>50 lines)
5. God objects (>3 ответственности)

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
- Описание назначения: Автоматический code review для выявления антипаттернов, дублирования кода, потенциальных багов и оптимизационных возможностей.
