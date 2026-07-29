# AIOS v11.9.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4183, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🎯 Dedup Threshold Auto-Tuner

Since v11.4 the near-duplicate cut-off was a fixed 0.92 guess. v11.9.0
tunes it against REAL compressed signatures:
`tune_dedup_threshold(vectors, compressor, score, candidates)` runs the
full union-find clustering once per candidate (default scan:
0.80/0.85/0.90/0.92/0.95/0.98) and scores each as **duplicates ×
avg_similarity** — merge as many true duplicates as possible, but weight
the merge by intra-group confidence. Ties break toward the HIGHER
threshold (merging is irreversible, so equal quality prefers the
conservative cut-off); a scan with zero duplicates keeps the factory
default. Tuning never merges anything — it only recommends.

`AgentMemorySystem.tune_dedup_threshold(pool, candidates, apply=)` wraps
this over the live index; `apply=True` promotes the recommendation to
the system's default `dedup_threshold`, which is:

- exposed in `dedup_stats()["threshold"]`,
- **persisted in snapshots** (older snapshots restore the 0.92 default),
- honored by `GET /api/memory/duplicates` when no explicit `?threshold=`
  is passed (an explicit parameter still wins).

API: `POST /api/memory/dedup/tune` (`candidates` / `pool` / `apply`,
400 on invalid input). The Near-Duplicate Groups panel has a Tune
button with live rationale feedback. On the demo-seeded system the tuner
correctly recommends 0.80 — it spots the four near-identical episodic
records the fixed 0.92 missed.

### ⬇️ Dispatch History CSV Export

`SubstrateConvergenceEngine.export_history_csv(limit=None)` renders the
dispatch history as RFC-4180 CSV (csv-module quoting — task ids with
commas/quotes/newlines round-trip, UTC ISO8601 timestamps). Served as a
file download:

```
GET /api/substrate/history/export?limit=  →  text/csv attachment
```

The Live Dispatch Router panel links it as **Export CSV**.

### ❤️ Aggregate Health Score

`aios_core/health_score.py` condenses the three runtime pillars into a
single 0..100 score:

| Component | Weight | Signal |
|---|---|---|
| substrate_fleet | 0.4 | mean health of ACTIVE substrates |
| scheduler_efficiency | 0.3 | 60% savings vs baseline + 40% non-fallback rate |
| memory_vitality | 0.3 | entry-count-weighted average strength |

Components carrying no signal (a scheduler with zero dispatches, an
empty memory) are dropped and weights **renormalized** — a cold system
reports a fair score instead of a misleading zero. Status thresholds:
`healthy` ≥ 80, `degraded` ≥ 50, `critical` below; `no_data` when
nothing was available. Served at `GET /api/health/score` and rendered as
the System Health Score panel on `/substrate`.

## Compatibility

- Additive only; explicit `?threshold=` on the duplicates endpoint keeps
  precedence over the tuned default. Snapshot format stays
  `SNAPSHOT_FORMAT = 1` (the new `dedup_threshold` key is optional on
  load).

## Tests

27 new — `test_dedup_tuning.py` (11: tie-break, confidence-weighted
scoring, default-keeping, empty index, validation, real-index
recommendation, apply + snapshot persistence, endpoint + panel),
`test_health_score.py` (10: cold-system neutrality, degraded bands,
fallback drag, component absence, inactive exclusion, no_data, endpoint
+ panel), `test_history_export.py` (6: header/rows/quoting, limit, empty
history, endpoint download/limit, panel link).
Suite total: **~4183 tests, 0 failures**; ruff clean; mkdocs strict OK;
GitHub Actions green.
