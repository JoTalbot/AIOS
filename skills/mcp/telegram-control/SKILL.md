---
name: telegram-control
version: 1.0
description: Локальный сервер для операций Telegram Bot API и управлением персональным аккаунтом через MTProto
triggers: [telegram_task, bot_operation]
dependencies: []
llm_required: false
mcp_tools: [bot_get_me, bot_send_message, bot_set_webhook, bot_delete_webhook, bot_get_webhook_info]
---

# Skill: Telegram Control MCP

## Описание

Этот скил предназначен для...

Use local server `http://127.0.0.1:8898` for Telegram Bot API operations and gated personal-account MTProto operations.

## Safe defaults
- Bot API tools enabled when `TELEGRAM_BOT_TOKEN` exists.
- Personal account automation disabled until API_ID/API_HASH, interactive login, and explicit env gate.
- BotFather cannot be controlled via Bot API; use `botfather_create_bot_plan` for draft steps, then MTProto only after explicit consent.
- No spam, no mass unsolicited messaging, respect FloodWait/rate limits.

## Tools
- bot_get_me
- bot_send_message
- bot_set_webhook
- bot_delete_webhook
- bot_get_webhook_info
- user_status
- user_login_requirements
- botfather_create_bot_plan
- user_send_message (blocked by default)

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
- Описание назначения: Операционный навык Octopus: telegram-control.
