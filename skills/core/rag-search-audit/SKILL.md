---
name: rag-search-audit
description: Аудит RAG (Retrieval-Augmented Generation) поиска для проверки качества retrieval и relevance.
---

# RAG Search Audit

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/rag-search-audit`

## Описание
Аудит RAG (Retrieval-Augmented Generation) поиска для проверки качества retrieval и relevance.

## Цели
- Проверка качества RAG retrieval
- Детекция проблем с RAG
- Мониторинг relevance поиска
- Оптимизация индексов RAG

## Рутины

### `audit_rag_search.py**
```python
# Аудит RAG поиска
# Проверка retrieval quality
```

### `check_rag_index.py**
```python
# Проверка RAG индекса
# Функция: check_rag_index_completeness()
```

### `detect_rag_issues.py**
```python
# Детекция проблем с RAG
# Функция: detect_rag_issues()
```

## Метрики
- `retrieval_quality_score`: Оценка качества retrieval
- `index_completeness_pct`: Компактность индекса (%)
- `relevance_score`: Релевантность поиска (%)
- `search_latency_ms`: Задержка поиска (ms)
- `rag_issues_found`: Найдено проблем RAG

## Пример использования
```bash
# Аудит RAG поиска
python3 code/audit_rag_search.py

# Проверка индекса
python3 code/check_rag_index.py

# Детекция проблем
python3 code/detect_rag_issues.py
```

## Векторный coverage
- ✅ RAG search quality
- ✅ RAG index audit
- ✅ RAG issues detection
- ✅ Relevance monitoring

## Anti-patterns to fix
1. Poor retrieval quality
2. Incomplete RAG index
3. Irrelevant search results
4. Slow RAG search
5. No RAG fallback

## RAG best practices
- High relevance scores (>0.8)
- Complete index coverage
- Fast retrieval (<100ms)
- Proper vector embeddings
- Regular index updates

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
- Описание назначения: Аудит RAG (Retrieval-Augmented Generation) поиска для проверки качества retrieval и relevance.
