# AIOS v11.13.0 — Release Notes

**Date:** 2026-07-30 · **Tests:** ~4284, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🗑️ Dispatch-History Retention — preview first, purge guarded

Since v11.4 every executed dispatch has been appended to the engine
history without any way to age it out. v11.13 adds retention management
following the established preview pattern:

```json
POST /api/substrate/history/preview {"keep_last": 500, "older_than_seconds": 86400}
{ "dry_run": true, "total_records": 5210, "would_remove": 4710,
  "would_remain": 500, "protected_by_keep_last": 500,
  "oldest_remaining_timestamp": 1785366599.8 }
```

A record survives when it is within the newest `keep_last` entries **or**
newer than the age cutoff — the preview dry-runs the exact criteria of
`purge_history()`, so the operator sees precisely what the purge will do.
The purge itself is irreversible, so
`POST /api/substrate/history/purge` requires `{"confirm": true}` (400
otherwise, pointing at the preview). The substrate dashboard grows a
**History Retention** panel with Preview and a red, browser-confirmed
Purge button.

### ⚡ Energy Budget — reconfigurable at runtime, persisted across restarts

The rolling energy budget (v11.5) was fixed at construction.
`EnergyAwareScheduler.configure_budget(limit, window_seconds=None)`
replaces it while the scheduler is live — and **carries every spend that
still falls inside the new window into the new budget**, so raising a
limit at runtime can never silently reset the window accounting.

```json
POST /api/substrate/budget {"limit": 150, "window_seconds": 7200}
{ "old": {"limit": 100.0, "spent": 12.4, ...},
  "new": {"limit": 150.0, "window_seconds": 7200.0, "spent": 12.4, ...},
  "carried_spends": 3, "carried_cost": 12.4,
  "budget_file": "/home/user/.aios/energy_budget.json" }
```

`save_budget()` / `load_energy_budget()` persist the configuration as
tagged JSON (`format: 1`): a missing file returns None, malformed,
wrong-format, non-numeric or negative content raises ValueError, and the
dashboard falls back to the built-in default in that case. The **Energy
Budget** panel shows limit/window/spent/remaining live with an Apply
form — the configuration survives dashboard restarts.

### 📈 Policy-Projection Prometheus Series — the A/B matrix, continuously

v11.12 answered "which policy would run this batch cheapest?" on demand.
v11.13 makes it scrapeable: `render_prometheus(...,
policy_projection_records=N)` reconstructs the newest N dispatch records
(≤ 500, same energy→units rule as the replay) and exports the compare
matrix as gauges:

```
aios_policy_projection_tasks 100
aios_policy_projection_energy{policy="min_energy"} 12.4
aios_policy_projection_delta_vs_reference{policy="balanced"} 0.9
aios_policy_projection_recommended{policy="min_energy"} 1
```

`GET /api/metrics` enables the block with the newest 100 records. The
parameter defaults to 0 (off), so existing scrapes are unchanged; empty
history omits the block, unknown substrates fall back to 1 compute unit,
and exactly one policy is flagged recommended.

## Compatibility

- Preview/purge and budget endpoints are additive; the purge endpoint
  refuses to delete without explicit `{"confirm": true}`.
- Budget reconfiguration never drops in-window spend accounting, and a
  missing/malformed budget file falls back to the previous default.
- The policy-projection series is opt-in for library callers and
  additional-only for the `/api/metrics` exposition.

## Tests

29 new — `test_history_purge.py` (13: keep_last/age/union criteria,
validation, dry-run immunity, endpoint guard + round-trip, UI panel),
`test_budget_config.py` (10: carry-over semantics, window shrink,
validation, save/load round-trip incl. malformed files, endpoint
apply+persist+restart reload), `test_metrics_projection.py` (6: series
per policy, exactly-one recommended, reference delta zero, opt-in
default, unknown-substrate fallback, endpoint exposition).
