# AIOS v11.11.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4233, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🔁 History Replay / Routing-Drift Analysis

v11.9 let you export dispatch history to CSV; v11.8 let you forecast a
batch. v11.11 closes the loop: `EnergyAwareScheduler.replay(records,
policy=)` takes recorded dispatches (one row per CSV record or an
equivalent dict) and re-plans each against the CURRENT engine state —
answering **"would the router make the same choices today, and how much
energy would a different policy save?"**

- Compute units are recovered **exactly** from
  `recorded energy_cost ÷ substrate cost-per-unit` (the same formula
  dispatch uses), unless the record says otherwise via `compute_units`.
- Per-record comparison: recorded vs planned substrate, energy delta,
  `matching` flag; batch roll-up: `match_pct`,
  `recorded/planned_energy_total`, `potential_savings`, and
  `unknown_substrates` (retired names from old exports get flagged, not
  silently re-planned).
- Pure dry-run: nothing executes or gets recorded.

API: `POST /api/substrate/replay` accepts **both** JSON
`{"records": [...], "policy"}` and raw CSV export text (policy via
`?policy=`); malformed bodies get precise 400s. The Dispatch Forecast
panel has a **Replay CSV** file picker — export from the Router panel,
replay under a different policy, watch the savings estimate.

### 🧊 Archive Dry-Run Preview

`AgentMemorySystem.preview_archive_dead(min_strength, min_age_days)`
applies the EXACT "dead" criterion of `archive_dead()` (decayed strength
below the floor AND age at least `min_age_days`) and reports what WOULD
move to cold storage — ids with per-entry age/strength plus
`counts_after` — without moving a single entry. Lifecycle operations now
share one pattern: **preview (v11.10 dedup, v11.11 archive) → verify →
run**. API: `POST /api/memory/archive/preview`; a Preview button sits in
the Memory Lifecycle panel right next to the real Archive run.

### 📊 Health / SLO Prometheus Series

`GET /api/metrics` now evaluates default SLO thresholds (80/50) on every
scrape and exports:

- `aios_health_score` — the v11.9 aggregate score as a gauge,
- `aios_health_evaluated_components` — how many pillars carried signal,
- `aios_slo_ok` — 1 when no threshold is violated (clean alert rule),
- `aios_slo_alerts{severity="warning"|"critical"}` — active alert counts
  by severity.

Grafana can now graph the health slope and fire on
`aios_slo_ok == 0` — no dashboard JSON parsing required.
`evaluate_health_alerts()` gained the `evaluated` field for this.

## Compatibility

- Purely additive: replay/preview never mutate; `/api/metrics` gains
  series but changes no existing ones; JSON-mode replay ignores the CSV
  `?policy=` query param (documented behaviour).

## Tests

24 new — `test_replay.py` (10: exact unit reconstruction, drift with a
cheaper substrate, unknown-substrate flagging, policy override,
explicit-units precedence, validation, CSV round-trip via export,
JSON path, panel picker), `test_archive_preview.py` (8: parity with the
real `archive_dead()`, existing-archive counts, age floor, validation,
endpoint and button), `test_metrics_slo.py` (6: series presence/absence,
severity roll-up, no-data, endpoint healthy/damaged).
Suite total: **~4233 tests, 0 failures**; ruff clean; mkdocs strict OK;
GitHub Actions green.
