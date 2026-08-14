# Сессия: герметизация failing tests

---
session_id: "20260814T100000Z-aios-arena-test-hermeticity"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T10:00:00Z"
updated_utc: "2026-08-14T10:00:00Z"
branch: "agent/20260814-test-hermeticity"
base_commit: "e5c107da"
claim: "coordination/claims/test-hermeticity--20260814T100000Z-aios-arena-test-hermeticity.md"
---

## Цель

Сделать шесть baseline failures герметичными без изменения production-кода и protected LLM balancer.

## Scope

- Только `tests/test_account_control_dialog.py`, `tests/test_ops_monitoring.py`, `tests/test_v18_v19_fintech_e2e.py`, handoff.
- Запрещены live LLM/network, `/root/AIOS/data`, production logs и credentials.

## План

Исправить module alias mocks, временные data roots, fake provider/log и deterministic wallet income fixture; затем повторить failing tests и полный suite.
