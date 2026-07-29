# AIOS v11.8.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4156, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🔮 Batch Dispatch Forecasting

`EnergyAwareScheduler.forecast(tasks, policy=None)` simulates a whole
batch of dispatches (up to 1000 tasks) against the CURRENT engine state —
without executing, recording or learning anything (`report()`, the
rolling budget and the engine history are provably untouched).

The rolling energy budget is projected **cumulatively**: a task that
would be affordable on its own is flagged `projected_budget_exceeded`
once the earlier tasks in the batch have consumed the remaining window.
Every forecast entry reports the selected substrate, expected energy /
latency, an `affordable` flag, violations and the running
`cumulative_energy`; the batch summary adds projected totals and the
`window_remaining_after`.

```python
scheduler.forecast(
    [{"id": "f1", "category": "general", "compute_units": 10}],
    policy="min_energy",
)
```

Served via `POST /api/substrate/forecast` (`{"tasks": [...], "policy":
optional}`, 400 on invalid payloads) and editable right on `/substrate`
in the new **Dispatch Forecast** panel (JSON batch editor + projection
list).

### 💾 Memory Snapshot APIs

The v11.6 persistence engine gets dashboard endpoints:

- `POST /api/memory/snapshot/save` — atomic write of the live memory
  system, optional `{"path"}` (default `~/.aios/memory_snapshot.json`),
  response includes pool totals.
- `POST /api/memory/snapshot/load` — full format-versioned restore that
  REPLACES the live state (missing file → 404, corrupt / wrong format →
  400).

The `/memory` page gains a **Snapshot Persistence** panel (path input,
Save / Load buttons, live result feedback).

### 📈 Prometheus Metrics Export

New `aios_core/metrics_export.py` renders the live singletons — agent
memory, substrate convergence engine, energy-aware scheduler — in the
Prometheus text exposition format, scraped at:

```
GET /api/metrics   →  text/plain; version=0.0.4; charset=utf-8
```

Series include: `aios_info{version}`, per-pool and per-platform memory
gauges (`aios_memory_entries`, `aios_memory_platform_entries`,
`aios_memory_avg_strength`), dedup + compression counters
(`aios_memory_dedup_removed_total`, `aios_memory_compression_*`), engine
state and per-substrate analytics (`aios_substrates`,
`aios_engine_dispatches_total`, `aios_engine_substrate_*`), and the full
scheduler set (`aios_scheduler_dispatches_total`,
`aios_scheduler_policy_dispatches_total{policy}`,
`aios_scheduler_budget{field=limit|spent|remaining}`, …).
Rendering is pure stdlib string building with label escaping and
non-finite guarding; missing sources simply omit their block.

## Compatibility

- No breaking changes: all new APIs are additive; existing
  `plan()/dispatch()` and memory endpoints behave exactly as in v11.7.0.
- `forecast()` accepts the same policies (`min_energy` … `ai_optimized`)
  and the same per-call override semantics as `plan()`.

## Tests

27 new — `test_dispatch_forecast.py` (14: state purity, cumulative
projection, budget flags, spent-window shrinkage, policy override,
validation, no-route handling, no-budget mode, empty batch, endpoint +
panel), `test_metrics_export.py` (7: core series, sample well-formedness,
label escaping, missing sources, finite values, endpoint shape + live
coupling), `test_memory_snapshot_api.py` (6: save/load round-trip,
default path, missing/corrupt files, bad bodies, panel).
Suite total: **~4156 tests, 0 failures**; ruff clean; mkdocs strict OK;
GitHub Actions green.
