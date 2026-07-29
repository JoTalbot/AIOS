# AIOS v11.5.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4089, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🎯 Adaptive Compression Tuner

The v11.3.0 vector compressor used a fixed 64-dimension target. v11.5.0 adds
`AdaptiveTuner` (`aios_core/memory_compression.py`): it probes recall quality
directly — a handful of entries serve as pseudo-queries, and per candidate
dimension the tuner measures how well compressed rankings track dense
rankings (mean top-k `ranking_overlap`). The smallest dimension meeting
`min_overlap` wins; if none qualifies, the largest is kept (quality beats
savings).

```python
from aios_core.agent_memory_system import AgentMemorySystem

mem = AgentMemorySystem()
# ... record memories ...
report = mem.optimize_storage_adaptive(min_overlap=0.8, top_k=5, dims=[16, 32, 64, 128])
report["adaptive"]
# {"selected_dim": 32, "scores": {"16": 0.71, "32": 0.86, ...}, ...}
```

The selection persists in `compression_stats()["adaptive"]`, and recall
(`recall_compressed`) is coherent with the chosen dimension.

### 🧊 Cold-Storage Memory Archive

Long-term memories decay over time. `archive_dead()` moves entries that are
both weak (strength < `min_strength`) and old (>= `min_age_days`) out of the
active pool and the compressed index into an inspectable archive — memory
lifecycle is now complete: **record → consolidate → deduplicate → archive**.

```python
mem.archive_dead(min_strength=0.05, min_age_days=30.0)
mem.archived(limit=10)  # serialised archived entries
mem.stats()["archive"]  # {"archived_total": N, "last_report": {...}}
```

APIs: `GET /api/memory/archive` (listing), `POST /api/memory/archive/run`
(execute with optional `{"min_strength", "min_age_days"}`).

### ⚡ Energy Scheduler Panel (Substrate Dashboard)

`/substrate` now ships a live scheduler section:

- **Report card** — policy dispatches, fallbacks, energy spent / saved vs the
  engine baseline, savings %, rolling-budget remainder (new
  `GET /api/substrate/scheduler`).
- **Dry-run plan form** — pick a category and compute units, get the
  energy-optimal substrate and the expected savings without executing
  anything (backed by v11.4.0's `POST /api/substrate/schedule`).

## CI Milestone: emulator chain green end-to-end

The manual Full CI/CD pipeline (Lint → Calibrate prom/big/shafa →
Integration with emulators → GA simulation) went fully green for the first
time after a 3-round debugging campaign on real run logs:

1. `ANDROID_HOME` is now exported inside the emulator scripts themselves
   (the runner preset shadowed the custom SDK root → broken AVD path).
2. apkeep source aliases normalized to canonical values (`apk-pure`, …);
   uiautomator dump collection retries transient "null root node" races.
3. Environment-dependent outbox test pinned to a bogus serial; artifact
   dump XMLs flattened from `/tmp/tmp/*.xml` back to `/tmp/`.

## Bug Fix

- `_ensure_compressor` recreates the compressor when a different
  `target_dim` is requested (the first dim used to stick for the lifetime
  of the memory system).

## Compatibility

- All v11.3/v11.4 APIs unchanged; `stats()` / `compression_stats()` only
  gain new keys. No new dependencies.

## Tests

23 new: `test_adaptive_compression.py` (10), `test_memory_archive.py` (10),
`test_substrate_dashboard.py` (+3 scheduler panel/report).
Full suite: **~4089 passed, 0 failed**; `ruff check` + `ruff format --check`
clean; `mkdocs build --strict` clean.
