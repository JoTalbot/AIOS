---
name: security-port-guard
version: 1.0
description: Мониторинг открытых портов и предотвращение несанкционированных прослушивателей
triggers: [periodic_check, security_audit]
dependencies: []
llm_required: false
mcp_tools: []
---

# SKILL: security-port-guard

## Описание

Этот скил предназначен для...
Мониторинг открытых портов и предотвращение появления несанкционированных прослушивателей.

## Инструкции
1. Регулярно запускать `ss -tlnp`.
2. Сверять с разрешенным списком (8000, 9500, 9555, 9566, 9571, 11434).
3. Алертить при появлении чужих портов.

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
- Описание назначения: Операционный навык Octopus: security-port-guard.
