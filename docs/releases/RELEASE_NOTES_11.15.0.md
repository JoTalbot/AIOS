# AIOS v11.15.0 — Release Notes

**Date:** 2026-07-30 · **Tests:** ~4339, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🧊 Archive Retention — the third store joins the story

Engine history (v11.13) and scheduler dispatches (v11.14) already had
retention; the memory cold-storage archive — the destination of every
"dead" memory since v11.5 — still grew forever.
`preview_archive_purge()` / `purge_archive(keep_last, older_than_days)`
close the gap with the identical protected-union selection, except the
age criterion is in **days** (like every other memory API), converted
for the shared planner:

```json
POST /api/memory/archive/purge {"confirm": true, "keep_last": 100, "older_than_days": 90}
{ "removed": 430, "removed_ids": ["mem_12", ...], "remaining": 100,
  "purged_at": ... }
```

Under the hood `plan_retention_purge` gained a `timestamp_of` accessor
(so it works on `MemoryEntry` objects, not just dicts) and a
caller-named age criterion — a validation error for the archive names
`older_than_days`, never a foreign unit. Purged entries are deleted,
NOT returned to active pools. The Memory Lifecycle panel gains proper
Purge archive controls: keep/older inputs, Preview, red Purge.

### 🚦 Budget Pressure Rolls Up Into Unified Health Alerts

Two alert reports (health SLO + budget pressure) meant two places to
watch. `evaluate_health_alerts()` now evaluates budget pressure
alongside the health pillars:

```json
GET /api/health/alerts
{ "ok": false, "worst_severity": "warning",
  "alerts": [..., { "subject": "energy_budget", "severity": "warning",
                    "pressure": 0.9, "message": "..." }],
  "budget": { "status": "warning", "pressure": 0.9, ... } }
```

`alert_count`, `worst_severity` and `ok` all account for budget
exhaustion; custom ratios via `budget_warning_ratio` /
`budget_critical_ratio`. Schedulers WITHOUT a budget and calm budgets
produce byte-identical previous results. Because the report feeds
`GET /api/health/alerts` AND the Prometheus SLO block, the
`aios_slo_alerts{severity}` gauges now count budget alerts
automatically — one scrape covers fleet, scheduler, memory AND money.

### 📸 Snapshot Rotation — backups with a bound

Every `save()` overwrote the one snapshot file: a fat finger or a
half-written state and the backup story was gone.
`save(path, keep_rotated=N)` rotates the previous live file to
`<stem>.1<suffix>`, shifts older generations (.2, .3, ...), and drops
anything beyond N — the directory holds the live file plus at most N
loadable backups:

```
memory_snapshot.json        ← live (rotation 0)
memory_snapshot.1.json      ← previous generation
memory_snapshot.2.json
```

`keep_rotated=0` is the exact previous behaviour; values are validated
(int, 0..50, `ValueError`/HTTP 400 otherwise) and failed validation
writes nothing. `GET /api/memory/snapshot/list?path=` enumerates live
+ rotations with sizes and mtimes (gap-tolerant), the Snapshot
Persistence panel gains a Keep rotated input and a List button, and
every rotation passes through the normal `load()` path — each one is a
fully restorable snapshot.

## Compatibility

- Preview endpoints stay read-only; both archive and history purges
  require `{"confirm": true}`.
- The health-alerts roll-up only *adds* the `budget` key and budget
  alerts — unchanged output whenever no budget pressure exists.
- `save()` without `keep_rotated` is byte-identical to v11.14.

## Tests

26 new — `test_archive_purge.py` (9: keep/age/union criteria,
validation, dry-run immunity, endpoint guard + effect + pool
isolation), `test_health_rollup.py` (8: no-budget compatibility,
warning/critical roll-up, worst-severity dominance, custom ratios,
Prometheus counters, endpoint sub-report), `test_snapshot_rotation.py`
(9: shift/drop mechanics, fresh rotation, validation, gap-tolerant
listing, endpoint round-trip incl. loading a rotation, UI controls).
