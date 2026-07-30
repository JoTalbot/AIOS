---
name: browser-vision
version: 1.0
description: Локальный сервер автоматизации браузера и визуального контроля
triggers: [browser_task, visual_testing]
dependencies: []
llm_required: false
mcp_tools: [status, start, navigate, screenshot, click, type, press, text]
---

# Skill: Browser Vision MCP

## Описание

Этот скил предназначен для...

Local browser automation and visual control server at `http://127.0.0.1:8897`.
Public operator UI: `https://browser.autosklo.org.ua/` Basic Auth `user / 111111`.

Tools: status, start, navigate, screenshot, click, type, press, text, google_status, open_google_login.

Safety:
- User-owned accounts only.
- Human manually logs into Google in browser UI; passwords/2FA are not sent to AI chat.
- No CAPTCHA/2FA bypass.
- Click/type/press require approved=true.
- Use for drafts and operator-supervised workflows; sensitive/financial/destructive actions require explicit approval.

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
- Описание назначения: Операционный навык Octopus: browser-vision.
