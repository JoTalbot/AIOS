---
name: log-summarizer
version: 1.0
description: Агрегация и суммаризация логов из journalctl
triggers: [log_review, log_analysis, debugging]
dependencies: []
llm_required: false
mcp_tools: []
---
# Log Summarizer Skill

## Описание
Агрегирует логи из journalctl, выделяет паттерны ошибок.

## Features
- Grouping by error type
- Count occurrences
- Extract timestamps
