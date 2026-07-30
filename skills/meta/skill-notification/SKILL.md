---
name: skill-notification
version: 3.0
description: Отправка уведомлений человеку через Telegram и логирование
triggers: [notify, autonomous_agent_complete, alert]
dependencies: []
llm_required: false
mcp_tools: []
---
# Skill Notification

## Описание
Отправляет уведомления человеку через Telegram бот (YakForumsBot) и записывает в журнал автономии.
Обеспечивает обратную связь о действиях автономного агента.

## Входные данные
- message: текст уведомления
- level: info/warning/critical (default: info)
- channel: telegram/log/both (default: both)

## Выходные данные
- success: bool
- delivery confirmation

## Алгоритм
1. Форматировать сообщение с timestamp и level
2. Записать в autonomy_journal
3. Попытаться отправить в Telegram (если бот доступен)
4. Вернуть статус доставки

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
