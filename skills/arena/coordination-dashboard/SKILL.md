---
name: coordination-dashboard
version: 1.0
description: Детерминированно строит центральный статус AIOS из session journals и claims, выявляя stale metadata.
triggers: [agent-status, coordination-dashboard, stale-claim, session-handoff]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# Coordination Dashboard

## Описание

Использовать, когда нужно получить единый статус параллельных агентов без ручного
копирования данных. Источники истины — `coordination/sessions/*.md` и
`coordination/claims/*.md`; dashboard является только производным представлением.

## Алгоритм

1. Проверить `git status`, прочитать protocol/context и активные claims.
2. Выполнить `python scripts/generate_agents_status.py`.
3. Просмотреть активные/paused/blocked sessions и раздел несогласованностей.
4. Проверить детерминизм: `python scripts/generate_agents_status.py --check`.
5. Перед CI использовать `--check`, а не сравнивать timestamps: генератор не включает
   время запуска, поэтому одинаковые входы дают одинаковый Markdown.
6. Stale ACTIVE claim при DONE-session и завершённый claim, оставшийся в каталоге,
   считать metadata inconsistency; не удалять чужой claim автоматически.

## Контроль и развитие

- [x] Unit-тесты parser/render/atomic write/check mode.
- [x] Запись через временный файл в том же каталоге + `os.replace`.
- [x] Markdown-значения нормализуются и экранируют `|`.
- [ ] Подключить `python scripts/generate_agents_status.py --check` в CI после периода наблюдения.
