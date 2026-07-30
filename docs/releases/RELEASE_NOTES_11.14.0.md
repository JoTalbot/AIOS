# AIOS v11.14.0 — Release Notes

**Date:** 2026-07-30 · **Tests:** ~4313, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🧹 Scheduler-Dispatch Retention — one retention story, both stores

v11.13 aged out the engine's dispatch history; the energy-aware
scheduler kept its own append-only list with the same growth problem.
`EnergyAwareScheduler.preview_purge_dispatches()` /
`purge_dispatches(keep_last, older_than_seconds)` manage it with the
**identical** protected-union selection — a record survives within the
newest `keep_last` **or** newer than the age cutoff. The shared logic
now lives in `aios_core/retention.py` (`plan_retention_purge`) and the
engine purge delegates to it, so both stores can never drift apart.

```json
POST /api/substrate/dispatches/purge {"confirm": true, "keep_last": 1000}
{ "dry_run": false, "removed": 4210, "remaining": 1000, "purged_at": ... }
```

Two hard guarantees: purging scheduler history never touches the engine
history (separate store, separate endpoint), and it never touches the
**budget ledger** — deleting history does not refund spent energy. The
History Retention panel gains a Target select (Engine history /
Scheduler dispatches) driving the same Preview / Purge buttons.

### 🔥 Budget Pressure Alerts — see exhaustion before dispatches fail

Budget-exceeded violations are the *late* signal. v11.14 adds the early
one: `RollingEnergyBudget.pressure()` = spent/limit (it can exceed 1.0 —
a runtime reconfigure may cut the limit below the current window's
spend), evaluated by `evaluate_budget_alerts()` against warning/critical
ratios (default 0.8/1.0):

```json
GET /api/substrate/budget/alerts
{ "available": true, "status": "warning", "pressure": 0.9,
  "alerts": [{ "subject": "energy_budget", "severity": "warning",
               "spent": 90.0, "limit": 100.0, "message": "..." }] }
```

`status` is `ok` / `warning` / `critical` / `no_budget`; custom ratios
via `?warning=&critical=` (400 when unordered or non-numeric). The
Energy Budget panel shows a live Pressure / Status row colored by
severity, `to_dict()` and the scheduler report now carry `pressure`
everywhere, and Prometheus gains `aios_energy_budget_pressure` — one
gauge your Alertmanager can threshold directly.

### 🕒 Recall/Search Age Filter

`recall(..., max_age_days=)` and the token `search(..., max_age_days=)`
exclude memories older than the given days (non-negative float,
validated). The search variant **pre-filters candidates before
scoring**, so scores, tie-breaks and pool selection behave exactly as
before — old entries simply never enter the candidate set. The web
recall endpoint applies the bound in BOTH modes:

```
GET /api/memory/recall?q=olx+login&mode=keyword&max_age_days=7
GET /api/memory/recall?q=login&mode=compressed&max_age_days=7
```

Non-numeric or negative values return 400 with a clear message. The
Recall Search panel gains a Max Age (days) field (empty = no limit).

## Compatibility

- Preview endpoints are read-only; both purge endpoints require
  `{"confirm": true}`.
- Budget alerting is additive; `pressure` appears next to existing
  budget fields without changing their semantics, and a scheduler
  without a budget cleanly reports `no_budget`.
- `max_age_days` defaults to None everywhere — unfiltered behaviour is
  byte-for-byte the previous one.

## Tests

29 new — `test_dispatches_retention.py` (11: shared-plan validation and
union semantics, dry-run immunity, budget-ledger and engine-history
isolation, endpoint guard + round-trip, Target select),
`test_budget_alerts.py` (10: pressure ratio incl. post-reconfigure >1,
ok/warning/critical bands and boundaries, ratio validation, endpoint
and Prometheus series), `test_age_filter.py` (8: recall/search
filtering + validation, endpoint in both modes, UI field).
