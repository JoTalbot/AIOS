---
name: api-rate-limit-audit
description: Аудит rate-limit настроек на публичных API endpoints Octopus.
---

# SKILL: api-rate-limit-audit
**Категория:** core
**Дата создания:** 2026-06-20

## Описание
Аудит rate-limit настроек на публичных API endpoints Octopus.

## Инструкции
1. Определить цель навыка.
2. Реализовать логику.
3. Добавить тесты.

## Назначение (конкретизировано)
Резервная заглушка преобразована в конкретный навык **api-rate-limit-audit**. Задача навыка — безопасно анализировать соответствующее направление, выдавать отчёт и предложения по развитию без деструктивных действий по умолчанию.

## Алгоритм
1. Найти API endpoint'ы проекта (FastAPI/router/app.route) в `repo/`, `services/`, `integrations/`, `api/`.
2. Для каждого файла проверить наличие rate-limit кода (паттерны: `rate_limit`, `X-RateLimit`, `throttle`, `limiter`, `maxRequests`).
3. Проверить, что rate-limit задекларирован с явным числовым значением (а не только упоминание).
4. Рассчитать score: 40% за наличие кода, 60% за явные значения.
5. Сформировать JSON-отчёт: api_sources_found, with_ratelimit_code, with_explicit_value, findings.
6. Read-only, без сетевых вызовов и без изменения системы.

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py` пересчитывает health/coverage и дописывает AI-предложения в `references/`.
- Развитие через ИИ: локальный Ollama/Qwen генерирует bounded improvement proposal; автоприменяются только безопасные структурные улучшения (алгоритм, тест, runtime wrapper).
- Описание назначения: Автоматически сгенерированный навык.
