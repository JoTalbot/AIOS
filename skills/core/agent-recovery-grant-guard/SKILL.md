---
name: agent-recovery-grant-guard
version: 1.0
description: Проверяет безопасную выдачу одноразового SSH grant через Telegram approval
triggers: [agent_recovery]
dependencies: []
llm_required: false
mcp_tools: []
---

# agent-recovery-grant-guard

## Описание

Этот скил предназначен для...

Проверяет безопасную выдачу одноразового SSH grant через Telegram approval.

## Алгоритм
1. Компилирует целевой `server.py` через `py_compile` (fail-fast на синтаксической ошибке).
2. Загружает исходник как текст и проверяет порядок операций выдачи ключа:
   a) `approval=reserve_approval(rid,secret)` — резерв до старта grant;
   b) `finish_approval_grant(rid,secret,False)` — откат в `approved` при ошибке pubkey;
   c) `finish_approval_grant(rid,secret,True)` — переход в `consumed` только после успеха.
3. Проверяет, что `meta=PROJECTS.get(project...)` встречается РАНЬШЕ, чем
   `ssh_user=meta.get(...)` после точки `reserve_approval` (project metadata до выбора SSH user).
4. Порт 2222 инвариантен и не переписывается.

## Контракт
- approval сначала резервируется со статусом `granting`;
- при ошибке публичного ключа возвращается в `approved`;
- `consumed` выставляется только после успешной установки ключа;
- project metadata определяется до выбора SSH user;
- порт 2222 не изменяется.

## Проверка
`python3 code/check.py /opt/octopus-agent-recovery/server.py`

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
