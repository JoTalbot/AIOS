# AIOS v11.12.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4255, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### ⚖️ Policy A/B Comparison Matrix

Four scheduling policies (v11.7) means four answers to "which substrate
should run this batch?" — `compare_policies(tasks, policies=None,
reference_policy=None)` runs the SAME batch as a dry-run under every
policy and lines the answers up:

```json
{ "matrix": {
    "min_energy":  { "projected_energy": 0.2, "substrate_choices": [...], "energy_delta_vs_reference": 0.0 },
    "min_latency": { "projected_energy": 2.0, "energy_delta_vs_reference": 1.8, "choice_overlap_vs_reference_pct": 0.0 },
    ... },
  "reference_policy": "min_energy", "recommended_policy": "min_energy" }
```

`recommended_policy` is the lowest projected energy — with ties breaking
**toward the reference**: switch policies only for a measurable win, not
for noise. Served at `POST /api/substrate/compare` and rendered by the
Compare A/B button on the Dispatch Forecast panel (uses the same JSON
batch editor as Forecast).

### 🔀 Guarded Dedup Merge — the workflow is complete

Since v11.4 the engine could merge near-duplicates, v11.9 tuned the
threshold, v11.10 previewed the plan — but pressing the actual button
required code. v11.12 exposes it:
`POST /api/memory/dedup/run` with a mandatory `{"confirm": true}` guard
(400 otherwise, pointing at `/api/memory/dedup/preview`). Optional
`threshold`/`pool` override the tuned default. The Near-Duplicate Groups
panel grows a red **Merge** button (browser-confirm + live report), so
the full loop **Tune → Preview → Merge** runs end-to-end in the UI.

### 🔍 Snapshot Diff

`AgentMemorySystem.diff_snapshot(snapshot_dict)` answers "what changed
since I saved?": added/removed/changed memory ids per pool (including
the archive), pattern drift, pool counts on both sides and metadata
drift (tuned dedup threshold, lifetime removed total). Equality uses the
persistence serialisation — derived strength is deliberately excluded —
so **passive ageing never produces phantom changes**, only real
mutations (records, merges, access-count absorptions) surface. Served
read-only at `POST /api/memory/snapshot/diff` (404 on a missing file,
400 on corrupt input) with a **Diff vs live** button on the Snapshot
Persistence panel showing `+added / −removed / ~changed`.

## Compatibility

- Additive only: compare/diff are dry-run/read-only; the dedup run
  endpoint refuses to merge without explicit confirmation.

## Tests

22 new — `test_snapshot_diff.py` (9: identity, adds/removes/changes,
pattern drift, decay-drift immunity, validation, endpoint round-trip),
`test_policy_compare.py` (7: full-matrix choices and deltas, subsets,
reference tie-break, validation, dry-run purity, endpoint and button),
`test_dedup_run.py` (6: confirm guard, seeded merge + idempotency,
threshold/pool params, tuned default, validation, button).
Suite total: **~4255 tests, 0 failures**; ruff clean; mkdocs strict OK;
GitHub Actions green.
