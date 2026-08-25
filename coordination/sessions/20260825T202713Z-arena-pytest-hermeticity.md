---
session_id: "20260825T202713Z-arena-pytest-hermeticity"
status: "DONE"
agent: "Arena.ai Agent Mode"
machine: "e2b.local"
started_utc: "2026-08-25T20:27:13Z"
updated_utc: "2026-08-25T20:36:00Z"
branch: "arena/01a03a3f-aios"
base_commit: "d0009aa3"
claim: "coordination/claims/pytest-hermeticity--20260825T202713Z-arena-pytest-hermeticity.md (снят при завершении)"
---

## Цель

Устранить переносимые full-pytest failures из-за hard-coded `/root/AIOS` и неверных legacy import paths без изменения production logic.

## Scope

- Разрешённые файлы: failing test files с path/import assumptions, собственные coordination/skill.
- Вне scope: live Kraken behavior, benchmark dependency policy, protected files, production deploy, OpenHands/accounting reporter claims.
- Пересечения: не обнаружены.

## Исходное состояние

- Worktree чист; PR #248 @ `d0009aa3`.
- Full pytest после успешной collection: 15 failures + 19 fixture errors; большая группа — PermissionError `/root/AIOS`, три — scripts import.
- Применён dependency-collection skill; отдельного hermeticity skill нет.

## План

1. Заменить hard-coded repo root на `Path(__file__).resolve().parents[1]`.
2. Импортировать scripts как package modules вместо `sys.path /root/AIOS/scripts`.
3. Прогнать затронутые тесты, full collection, ruff.
4. Skill/session/commit/push.

## Текущий шаг (виден другим агентам)

- Текущий шаг: DONE — 8 затронутых файлов, 100 tests passed; E/F hard gate и compile clean.
- Обновлено UTC: 2026-08-25T20:36:00Z

## Ход работы и решения

- 20:27Z — pytest docs подтверждают `tmp_path`/`monkeypatch` для изоляции; для read-only repository fixtures устойчивый корень вычисляется от `__file__`, не от cwd или machine-specific `/root/AIOS`.
- 20:27Z — repository research: `api_usage_report.py` и `business_digest.py` существуют в `scripts/`; failures вызваны только неверным hard-coded `sys.path`.
- 20:32Z — path constants в Telegram импортируются by-value, поэтому патч одного `PROJECT_ROOT` недостаточен; тестовый helper теперь перенаправляет constants в owning modules на `tmp_path/data`.
- 20:34Z — report/digest tests отделены от live production snapshots через минимальные детерминированные providers; проверяется wiring/render contract, не состояние host.
- 20:36Z — все 100 тестов восьми файлов прошли; changed-file E/F hard gate и py_compile зелёные.

## Изменённые файлы

- 8 `tests/test_*.py` — derived repo root, tmp mutable paths, deterministic report providers.
- `skills/arena/pytest-path-hermeticity/SKILL.md` — дистиллированный алгоритм.
- Этот журнал; claim снят.

## Проверки

- `[PASS]` targeted 8 files — 100 passed.
- `[PASS]` `ruff check --select E,F --ignore E402 <8 files>`.
- `[PASS]` `python -m py_compile <8 files>`.
- `[PASS]` `git diff --check`.

## Git

- Коммиты: ожидается test-only commit.
- PR: #248.
- Незакоммиченные изменения: test/session/skill до commit.

## Handoff

- Последняя завершённая точка: portable path/import group закрыта.
- Следующий шаг: commit/push; отдельными задачами — benchmark plugin, live-network isolation, missing xgboost/legacy modules.
- Блокеры: нет.
- Риски: legacy E501 подавлен только в трёх fixture-heavy test files; E/F остаются активны.
- Что нельзя делать: менять production logic/claimed files.
