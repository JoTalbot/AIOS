---
name: web-research
version: 2.0
description: Autonomous web research and data extraction via Browser Vision MCP
triggers: [research_needed, web_search, data_extraction, url_analysis, competitive_analysis]
dependencies: [browser-vision-mcp.service]
llm_required: false
---

# Skill: Web Research

## Description
Performs autonomous web research using the Browser Vision MCP server (port 8909).
Can navigate, extract text, links, screenshots, detect CAPTCHAs, capture network
requests, and return structured data. Read-only by default; interactive actions
require explicit approval.

## Input
- `query` or `urls` — search query or list of URLs to research
- `extract_links` — whether to extract links (default: true)
- `screenshot` — whether to take screenshots (default: false)
- `max_pages` — maximum pages to visit (default: 5)
- `depth` — link follow depth (default: 0, no following)

## Output
- Structured JSON with: url, title, text_excerpt, links, captcha_found, metadata

## Algorithm
1. Check Browser Vision MCP health (GET /health).
2. Start browser if not running (browser_start).
3. For each URL:
   a. Navigate (browser_goto).
   b. Detect CAPTCHA (browser_captcha_detect).
   c. Extract text (browser_snapshot).
   d. Extract links if requested (browser_extract_links).
   e. Screenshot if requested (browser_screenshot).
4. Close browser or leave running for subsequent calls.
5. Return structured results.

## Safety
- Read-only by default (no clicks, no form fills).
- Network capture requires approved=true.
- No password/cookie/2FA extraction.
- All URLs validated (no file://, chrome:// schemes).
- Bounded: max_pages prevents infinite crawling.

## Integration with Agent
The autonomous agent can call this skill via:
  python3 /root/agents/-Octopus/skills/core/web-research/code/web_research.py --urls "https://example.com" --output /tmp/research.json

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
- Описание назначения: Autonomous web research and data extraction via Browser Vision MCP
