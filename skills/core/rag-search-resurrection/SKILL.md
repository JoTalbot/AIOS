---
name: rag-search-resurrection
description: Восстановление и исправление RAG search после поломок для обеспечения поиска.
---

# RAG Search Resurrection

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/rag-search-resurrection`

## Описание
Восстановление и исправление RAG search после поломок для обеспечения поиска.

## Цели
- Восстановление RAG поиска после поломок
- Диагностика проблем RAG
- Автоматическое исправление
- Рестарт RAG сервисов

## Рутины

### `resurrect_rag_search.py`
```python
# Восстановление RAG поиска
# Функция: resurrect_rag_search()
```

### `diagnose_rag_issues.py**
```python
# Диагностика проблем RAG
# Функция: diagnose_rag_issues()
```

### `restore_rag_index.py**
```python
# Восстановление индекса RAG
# Функция: restore_rag_index()
```

## Метрики
- `rag_status`: Статус RAG
- `issues_detected`: Найдено проблем
- `restoration_time_seconds`: Время восстановления (сек)
- `index_completeness_pct`: Компактность индекса
- `search_latency_ms`: Задержка поиска

## Пример использования
```bash
# Восстановление RAG поиска
python3 code/resurrect_rag_search.py

# Диагностика проблем
python3 code/diagnose_rag_issues.py

# Восстановление индекса
python3 code/restore_rag_index.py
```

## Векторный coverage
- ✅ RAG resurrection
- ✅ RAG diagnosis
- ✅ RAG index restoration
- ✅ Search latency monitoring

## Anti-patterns to fix
1. RAG search broken
2. Index corruption
3. Search failure
4. No RAG fallback
5. Slow RAG response

## Common issues
- Index not found
- Vector embeddings missing
- Search timeout
- RAG service down
- Index outdated

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
- Описание назначения: Восстановление и исправление RAG search после поломок для обеспечения поиска.
