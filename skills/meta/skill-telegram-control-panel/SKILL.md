---
name: skill-telegram-control-panel
version: 1.0
description: Расширенная Telegram-панель управления Octopus с ReplyKeyboard, inline callbacks, audit trail, approval queue и безопасными bounded-действиями
triggers: [telegram, control_panel, callback_query, human_in_loop, approval]
dependencies: [skill-notification, skill-health-monitor, skill-autonomous-agent]
llm_required: false
mcp_tools: []
---
# Skill Telegram Control Panel

## Описание
Скилл формализует Telegram как основной человеко-ориентированный интерфейс управления Octopus.
Он не является отдельным push-отправителем: активный бот вызывает `/opt/octopus-agent-callbacks.py`, а отчёты автономного агента идут через `skill-notification`.

## Возможности
- Постоянное нижнее меню ReplyKeyboardMarkup для быстрых действий.
- Inline command-center для компактной навигации.
- `answerCallbackQuery` до тяжёлой работы в активном боте.
- Bounded systemd-запуски для циклов агента, skill evolution и all-vectors.
- Human-in-the-loop approval queue для рискованных действий.
- Audit trail всех кнопок и callback в `logs/telegram_control_audit.jsonl`.
- HTML/Markdown fallback без зависания ответа.

## Алгоритм
1. `/start`, `/menu`, `/control`, `/panel` показывают нижнее меню и inline command-center.
2. Текст кнопки из ReplyKeyboard передаётся в `handle_button(text)`.
3. Inline callback `agent:*` передаётся в `handle_callback(data)`.
4. Read-only команды выполняются сразу и возвращают краткий отчёт.
5. Долгие действия запускаются через systemd service/timer и не блокируют polling loop.
6. Опасные действия создают proposal в approval queue вместо мгновенного destructive выполнения.
7. Каждое действие пишет audit JSONL.

## Контроль и развитие
- Compile: `python3 -m py_compile /opt/octopus-tg-bot.py /opt/octopus-agent-callbacks.py`.
- Service: `systemctl status octopus-tg-bot.service`.
- Drift guard: `python3 scripts/telegram_drift_guard.py`.
- Skill evolution: `python3 scripts/skill_evolution_cycle.py`.
