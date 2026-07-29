# AIOS v11.10.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4209, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 👀 Dedup Merge Preview

Pressing merge on thousands of memories is a leap of faith — no longer.
`AgentMemorySystem.preview_dedup(threshold=None, pool="all")` dry-runs
the EXACT `deduplicate()` policy (strongest entry survives; it absorbs
access counts, best confidence and latest access) and reports what would
happen:

- per-group `absorbed_ids` and the projected representative stats
  (`access_count`, `confidence`, `strength`),
- `would_remove` and post-merge pool `counts_after`,
- all with `dry_run: true` and — provably in tests — zero state changes.

With `threshold=None` the preview uses the (possibly tuner-set) default,
so *Tune → Preview → Merge* forms a safe operator workflow. Served at
`POST /api/memory/dedup/preview` and wired to a Preview button on the
Near-Duplicate Groups panel.

### 🕐 Windowed Scheduler Report

`EnergyAwareScheduler.report(window_seconds=…)` aggregates only the
dispatches inside a sliding window — energy, savings, fallbacks and
per-policy counts scoped to e.g. the last hour, while the lifetime
totals stay one call away. `GET /api/substrate/scheduler?window=`
exposes it (400 on non-numeric/non-positive values, clamped at one
year), and the Energy Scheduler panel always shows a **Last Hour
(disp / spent)** stat.

### 🚨 SLO Alerts

`aios_core/slo_alerts.py` turns the v11.9.0 health score into actionable
alerts: the AGGREGATE score plus every available component (substrate
fleet, scheduler efficiency, memory vitality) is compared against
warning/critical thresholds — so an alert names the pillar that drags
the system down, not just the bruised total:

```
GET /api/health/alerts?warn=80&critical=50
→ {"ok": false, "worst_severity": "critical",
   "alerts": [{"subject": "substrate_fleet", "severity": "critical", ...}]}
```

Thresholds are validated (`0 <= critical < warning <= 100` → 400 on the
endpoint), severities roll up to `worst_severity`, and the System Health
Score panel on `/substrate` surfaces the alert summary next to the
score.

## Compatibility

- Additive only: `report()` without a window behaves exactly as before
  (existing callers and the v11.8 metrics export are untouched);
  `preview_dedup` never mutates; alert evaluation is read-only.

## Tests

26 new — `test_slo_alerts.py` (11: severity mix + worst roll-up,
       per-subject attribution, custom thresholds, validation, no-data,
       endpoint and panel), `test_dedup_preview.py` (9: merge-policy
       parity with the real `deduplicate()`, tuned-default usage,
       pool-split counts, validation, endpoint and button),
       `test_scheduler_window.py` (6: parity, old-dispatch exclusion,
       validation, endpoint window/clamp, panel stat).
Suite total: **~4209 tests, 0 failures**; ruff clean; mkdocs strict OK;
GitHub Actions green.
