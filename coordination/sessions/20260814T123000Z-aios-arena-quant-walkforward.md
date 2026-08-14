# Сессия: cost-aware walk-forward backtest

---
session_id: "20260814T123000Z-aios-arena-quant-walkforward"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T12:30:00Z"
updated_utc: "2026-08-14T12:30:00Z"
branch: "agent/20260814-quant-walkforward"
base_commit: "356ad7d1"
claim: "coordination/claims/quant-walkforward--20260814T123000Z-aios-arena-quant-walkforward.md"
---

## Цель

Реализовать полностью offline Directional-v2 walk-forward backtest по закрытым 1h OHLCV с fees/spread/slippage и out-of-sample evaluation.

## Ограничение

Runtime entry mode остаётся freeze; generator не делает network/order/state mutations, кроме отдельного report JSON.
