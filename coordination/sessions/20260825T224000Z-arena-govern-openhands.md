---
session_id: "20260825T224000Z-arena-govern-openhands"
status: "DONE"
agent: "Arena.ai Agent Mode"
machine: "e2b.local"
started_utc: "2026-08-25T22:40:00Z"
updated_utc: "2026-08-25T23:14:09Z"
branch: "arena/01a03a3f-aios"
base_commit: "9337609"
claim: "coordination/claims/govern-openhands--20260825T224000Z-arena-govern-openhands.md (снят при завершении)"
---

## Цель
Провести OpenHands Cloud run через канонический ArchitectureRuntime без изменения claimed `aios_core/openhands/**`.

## Текущий шаг (виден другим агентам)
- Текущий шаг: DONE — OpenHands Cloud run доступен как governed capability; no-cloud tests passed.
- Обновлено UTC: 2026-08-25T23:14:09Z

## Решения
- Реальный Cloud key отсутствует и Cloud может стоить денег; только FakeContour tests.
- Legacy HTTP router напрямую вызывает ContourService и пока не считается governed production path.

- 23:12Z — `OpenHandsCapabilityAdapter` реализует CapabilityEngine contract; `GovernedOpenHandsRunner` использует deterministic action ID для approval retry.
- 23:14Z — FakeContour подтверждает: policy deny/pending approval = 0 Cloud calls; approval = ровно 1 call + valid audit chain.

## Изменённые файлы
- architecture OpenHands adapter/exports, 2 tests, AIOS/OpenHands docs, skill.
- `aios_core/openhands/**` не менялся из-за чужого claim.

## Проверки
- `[PASS]` selected architecture/OpenHands set — 31 passed.
- `[PASS]` ruff, py_compile, diff check.

## Handoff
- Следующий шаг: commit/push/CI. Реальный Cloud launch — только после protected API key и consent на расходы.
- Блокер: `OPENHANDS_CLOUD_API_KEY` отсутствует; legacy HTTP router bypass остаётся.
