# Сессия: Cost-aware Directional Trading v2

---
session_id: "20260814T114000Z-aios-arena-trading-v2"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T11:40:00Z"
updated_utc: "2026-08-14T11:40:00Z"
branch: "agent/20260814-trading-v2"
base_commit: "b23bff63"
claim: "coordination/claims/trading-v2--20260814T114000Z-aios-arena-trading-v2.md"
---

## Цель

Реализовать выбранный владельцем Cost-aware Directional v2 в paper-only режиме.

## Runtime decision

`aios-quant-trading.service` остановлен на время разработки; market-data и ML остаются active. Реальные ордера не используются.

## Scope

- freeze новых entries по умолчанию;
- явные fee/spread/slippage costs;
- global drawdown/daily loss/cooldown guards;
- ML/RL veto и confidence gate;
- 1h closed-candle alignment;
- корректные entries/closes/wins/gross/fees/net accounting;
- новый чистый v2 paper state после проверки;
- regression/backtest gates до restart.
