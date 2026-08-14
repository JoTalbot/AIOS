# Сессия: декомпозиция quant report formatters

---
session_id: "20260814T113000Z-aios-arena-quant-formatters"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T11:30:00Z"
updated_utc: "2026-08-14T11:30:00Z"
branch: "agent/20260814-quant-formatters"
base_commit: "3858778e"
claim: "coordination/claims/quant-formatters--20260814T113000Z-aios-arena-quant-formatters.md"
---

## Цель

Вынести шесть чистых report formatters из `aios_core/quant_trading_engine.py` в отдельный модуль без изменения публичных импортов/вывода.

## Scope

Только pure formatting seam; торговая логика, state, adapters и `format_multi_exchange_demo_report` не меняются.
