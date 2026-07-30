# AIOS Changelog

All notable changes to this project will be documented in this file.

## [11.19.0] — 2026-07-30 — Dashboard Server REST API Endpoints for v11.16–v11.18 Features

### Added
- **REST API Auto-Throttle Endpoint (`GET / POST /api/substrate/budget/throttle`)**:
  - Exposes `EnergyAwareScheduler.configure_throttle` settings over HTTP JSON REST API.
- **REST API Policy Auto-Tune Endpoint (`POST /api/substrate/policy/autotune`)**:
  - Exposes `EnergyAwareScheduler.auto_tune_policy` recommendation & dynamic application endpoint.
- **REST API Memory Health Telemetry Endpoint (`GET /api/memory/health`)**:
  - Exposes `AgentMemorySystem.memory_health_report` vitality score, fragmentation ratio, and archive pressure.
- **REST API Snapshot Pruning Endpoint (`POST /api/memory/snapshot/prune`)**:
  - Exposes `AgentMemorySystem.prune_rotated_snapshots` for backup snapshot TTL cleanup.
- **REST API Retention Maintenance Engine Endpoint (`POST /api/retention/maintenance/run`)**:
  - Exposes guarded `RetentionMaintenanceEngine.run_maintenance_cycle` execution (`confirm: true`).

## [11.18.0] — 2026-07-30 — Multi-Tenant Energy Budget Allocation + Swarm Workload Balancing

### Added
- **Multi-Tenant Energy Budget Allocation (`MultiTenantBudgetAllocator`)**:
  - `MultiTenantBudgetAllocator` in `aios_core/multitenancy.py` manages tenant-level rolling energy budgets (`allocate_tenant_budget`) alongside a global energy budget cap.
  - Enforces quota affordability (`can_afford`) and tracks spend per tenant with aggregate reporting (`tenant_energy_report`).
- **Swarm Workload Balancing (`SwarmWorkloadBalancer`)**:
  - `SwarmWorkloadBalancer` in `aios_core/agent_swarm.py` distributes task batches across active swarm agents based on capability requirements, agent workload, and reputation.
  - Integrates with `EnergyAwareScheduler` to route assigned tasks through energy-aware substrate policies.
  - Provides workload efficiency reporting (`efficiency_report`).

## [11.17.0] — 2026-07-30 — Forecast Metrics Export + Policy Auto-Tuner + Memory Health Telemetry

### Added
- **Substrate Energy Forecast Metrics Export (`EnergyAwareScheduler.export_forecast_metrics`)**:
  - `export_forecast_metrics(tasks, policy)` translates batch forecast simulations into Prometheus gauge metrics dict (`aios_forecast_tasks_total`, `aios_forecast_projected_energy`, `aios_forecast_savings_vs_baseline`, etc.) for pre-dispatch observability.
- **Policy A/B Auto-Tuner (`EnergyAwareScheduler.recommend_optimal_policy` & `auto_tune_policy`)**:
  - `recommend_optimal_policy(tasks_sample)` evaluates recent workload dispatches or provided task samples across all policies (`min_energy`, `min_latency`, `balanced`, `ai_optimized`) using the A/B matrix and recommends the optimal energy-saving policy.
  - `auto_tune_policy(tasks_sample)` dynamically updates the active policy to the recommended choice.
- **Advanced Memory Health Telemetry (`AgentMemorySystem.memory_health_report`)**:
  - `memory_health_report()` computes fragmentation ratio, average entry strength, archive pressure score (0..100), and composite memory vitality score (0..100).

## [11.16.0] — 2026-07-30 — Dynamic Policy Auto-Throttling + Retention Maintenance Engine + Snapshot Auto-Pruning

### Added
- **Dynamic Policy Auto-Throttling (`EnergyAwareScheduler`)**:
  - `configure_throttle(enabled=True, threshold=0.8)` allows automatic routing policy downgrade.
  - When energy budget pressure reaches or exceeds `threshold` (default 0.8), dispatches dynamically downgrade from high-energy policies (`ai_optimized`, `balanced`, `min_latency`) to `min_energy` policy to conserve budget and prevent `energy_budget_exceeded` violations.
  - Dispatches report `"requested_policy"`, `"effective_policy"`, and `"throttled": True/False`.
- **Retention Maintenance Engine (`RetentionMaintenanceEngine`)**:
  - `RetentionMaintenanceEngine` in `aios_core/retention.py` provides unified, multi-store background retention cleanup across Substrate Engine history, Scheduler dispatches, and Memory Archive.
  - `run_maintenance_cycle()` executes maintenance purges in a single call and returns a unified status report.
- **Snapshot Auto-Pruning (`AgentMemorySystem.prune_rotated_snapshots`)**:
  - `prune_rotated_snapshots(path, max_age_days=30, keep_last=5)` automatically cleans up rotated backup snapshot files (`.1.json`, `.2.json`, etc.) exceeding age or depth limits, protecting the live snapshot file.
- **Audit & Code Quality Enhancements**:
  - Enhanced retention planner accessor fallbacks supporting custom objects with `timestamp` or `created_at` attributes.
  - Corrected Prometheus histogram bucket export calculations in `MetricsExporter.export()`.

## [11.15.0] — 2026-07-30 — Archive Retention + Budget Roll-Up Alerts + Snapshot Rotation

### Added
- **Cold-storage archive retention**
  (`AgentMemorySystem.preview_archive_purge()` /
  `purge_archive(keep_last, older_than_days)`): the third store joins
  the retention story (engine history v11.13, scheduler dispatches
  v11.14, memory archive now) with the identical protected-union
  selection — entry age in DAYS this time, converted for the shared
  `plan_retention_purge` (which gained a `timestamp_of` accessor and a
  caller-named age criterion so validation errors name your parameter).
  Purged entries are deleted, NOT moved back to active pools. APIs:
  `POST /api/memory/archive/purge/preview` (read-only) and guarded
  `POST /api/memory/archive/purge` (`{"confirm": true}`). The Memory
  Lifecycle panel gains Purge archive controls (keep/older inputs +
  Preview + red Purge).
- **Budget pressure in unified health alerts** —
  `evaluate_health_alerts(..., budget_warning_ratio=0.8,
  budget_critical_ratio=1.0)` now rolls `evaluate_budget_alerts` into
  the SAME report: subject "energy_budget" appears in `alerts`,
  `alert_count`, `worst_severity` and `ok`, with the full sub-report
  under the new `budget` key. No-budget schedulers and calm budgets
  produce byte-identical previous results. `GET /api/health/alerts`
  carries it; the `aios_slo_alerts{severity}` gauges count budget
  alerts automatically; one scrape now covers health pillars AND
  budget exhaustion. Dedicated endpoint stays available:
  `GET /api/substrate/budget/alerts`.
- **Snapshot rotation** — `save(path, keep_rotated=N)` rotates the
  previous live file to `<stem>.1<suffix>`, shifting older rotations
  and dropping generations beyond N (0 = off, the previous behaviour;
  validated int 0..50). `AgentMemorySystem.list_snapshot_files(path)`
  enumerates the live file + existing rotations (ordering, sizes,
  mtimes; gap-tolerant). APIs: `POST /api/memory/snapshot/save`
  accepts `keep_rotated` (400 on bad input, rotation report included)
  and read-only `GET /api/memory/snapshot/list?path=`. The Snapshot
  Persistence panel gains a Keep rotated input + List button; every
  rotation is a fully loadable snapshot.
- **Tests**: 26 new — `test_archive_purge.py` (9),
  `test_health_rollup.py` (8), `test_snapshot_rotation.py` (9).

## [11.14.0] — 2026-07-30 — Scheduler Retention + Budget Pressure Alerts + Recall Age Filter

### Added
- **Scheduler-dispatch retention** — the energy-aware scheduler keeps its
  own append-only dispatch list, now managed exactly like the engine
  history: `EnergyAwareScheduler.preview_purge_dispatches()` /
  `purge_dispatches(keep_last, older_than_seconds)` with the identical
  protected-union selection. Shared logic extracted into
  `aios_core/retention.py` (`plan_retention_purge`) used by BOTH stores
  (the engine purge was refactored to delegate — behaviour unchanged).
  Purging scheduler history never touches engine history or the budget
  ledger (a purge never refunds spend). APIs:
  `POST /api/substrate/dispatches/preview` (read-only) and guarded
  `POST /api/substrate/dispatches/purge` (`{"confirm": true}` required).
  The History Retention panel gains a Target select: Engine history /
  Scheduler dispatches.
- **Energy-budget pressure alerting** — `RollingEnergyBudget.pressure()`
  (spent/limit; can exceed 1.0 after a runtime reconfigure cuts the
  limit below current spend) and `evaluate_budget_alerts(scheduler,
  warning_ratio=0.8, critical_ratio=1.0)`: status ok/warning/critical/
  no_budget with machine-usable alert dicts (subject, severity,
  pressure, spent/limit, message). API: `GET
  /api/substrate/budget/alerts?warning=&critical=` (400 on unordered or
  non-numeric ratios). The Energy Budget panel shows a live Pressure /
  Status row colored by severity; Prometheus gains the
  `aios_energy_budget_pressure` gauge for external alert rules, and
  `to_dict()`/`report()` now carry the `pressure` field everywhere.
- **Recall/search age filter** — `recall(..., max_age_days=)` and
  token `search(..., max_age_days=)` exclude entries older than the
  bound (non-negative float, ValueError otherwise; the search filter
  pre-filters candidates before scoring, so scores and pool selection
  behave exactly as before). `GET /api/memory/recall` accepts
  `max_age_days=<float>` in BOTH keyword and compressed modes (400 on
  non-numeric/negative). The Recall Search panel gains a Max Age (days)
  field (empty = no limit).
- **Tests**: 29 new — `test_dispatches_retention.py` (11),
  `test_budget_alerts.py` (10), `test_age_filter.py` (8).

## [11.13.0] — 2026-07-30 — History Retention + Budget Persistence + Policy Projection Metrics

### Added
- **Dispatch-history retention management**
  (`SubstrateConvergenceEngine.preview_purge_history` /
  `purge_history(keep_last, older_than_seconds)`): a record survives when
  it is within the newest `keep_last` entries OR newer than the age
  cutoff — the preview dry-runs the exact mutator criteria (`dry_run`,
  `would_remove/would_remain`, protected count, cutoff and oldest
  survivor timestamps). APIs: `POST /api/substrate/history/preview`
  (read-only) and guarded `POST /api/substrate/history/purge` requiring
  `{"confirm": true}` (400 otherwise, pointing at the preview). History
  Retention panel with Preview + red Purge buttons.
- **Runtime energy-budget reconfiguration + persistence**
  (`EnergyAwareScheduler.configure_budget(limit, window_seconds=None)`):
  replaces the rolling budget while live; spends still inside the new
  window are carried over so reconfiguring can never silently reset
  window accounting. `save_budget(path)` persists limit/window as tagged
  JSON (`format: 1`), `load_energy_budget(path)` restores it (None for a
  missing file, ValueError for malformed/invalid/negative data). API:
  `POST /api/substrate/budget` — applies and persists to
  `~/.aios/energy_budget.json`; the dashboard seeds the scheduler from
  it on start, tolerant fall-back to the built-in default. Energy Budget
  panel shows limit/window/spent/remaining live with an Apply form.
- **Policy-projection Prometheus series**: `render_prometheus(...,
  policy_projection_records=N)` rebuilds the newest N dispatch records
  (clamped to 500) into tasks — same energy→units rule as the replay —
  and serves the v11.12 A/B compare matrix continuously:
  `aios_policy_projection_tasks`, `aios_policy_projection_energy{policy}`,
  `aios_policy_projection_delta_vs_reference{policy}` and
  `aios_policy_projection_recommended{policy}` (exactly one 1). Default
  0 keeps the exposition unchanged; `GET /api/metrics` enables it with
  the newest 100 records. Unknown substrates fall back to 1 compute
  unit; empty history omits the block entirely.
- **Tests**: 29 new — `test_history_purge.py` (12),
  `test_budget_config.py` (10), `test_metrics_projection.py` (7).

## [11.12.0] — 2026-07-29 — Policy Compare Matrix + Dedup Merge API + Snapshot Diff

### Added
- **Policy A/B comparison matrix**
  (`EnergyAwareScheduler.compare_policies(tasks, policies, reference_policy)`):
  dry-run forecasts of the SAME batch under every policy side by side —
  projected energy, affordable counts, per-task substrate choices, deltas
  and choice-overlap vs the reference; `recommended_policy` is the lowest
  energy with ties breaking toward the reference (switch only for a
  measurable win). API: `POST /api/substrate/compare`; Compare A/B button
  on the Dispatch Forecast panel.
- **Guarded dedup merge endpoint** `POST /api/memory/dedup/run` — the
  previously code-only `deduplicate()` is now reachable from the
  dashboard, completing the Tune → Preview → **Merge** workflow. Merging
  is irreversible, so the body MUST contain `{"confirm": true}` (400
  otherwise, pointing at the preview endpoint); optional threshold/pool
  overrides, tuned default otherwise. Merge button on the Near-Duplicate
  Groups panel.
- **Snapshot diff** (`AgentMemorySystem.diff_snapshot`): live state vs an
  on-disk snapshot — added/removed/changed ids per pool, pattern drift,
  counts on both sides, metadata drift (tuned threshold, lifetime removed
  total) and an `identical` flag. Entry equality uses the persistence
  serialisation (derived strength deliberately excluded), so passive
  ageing never produces phantom changes. API:
  `POST /api/memory/snapshot/diff` (read-only: 404 missing file, 400
  corrupt); Diff vs live button on the Snapshot Persistence panel.
- **Tests**: 22 new — `test_snapshot_diff.py` (9),
  `test_policy_compare.py` (7), `test_dedup_run.py` (6).

## [11.11.0] — 2026-07-29 — Replay Drift Analysis + Archive Preview + SLO Metrics

### Added
- **History replay / routing-drift analysis**
  (`EnergyAwareScheduler.replay(records, policy=)`): re-plans recorded
  dispatches (rows of the v11.9 CSV export) against the CURRENT engine
  state — compute units are recovered exactly from recorded
  energy/cost-per-unit — and reports matches, energy deltas, potential
  savings and unknown substrate names. Pure dry-run. API:
  `POST /api/substrate/replay` accepting BOTH JSON `{"records": [...],
  "policy"}` and raw CSV export text (policy via `?policy=`); 400 on
  malformed input. The Dispatch Forecast panel gains a Replay CSV picker.
- **Archive dry-run preview** (`AgentMemorySystem.preview_archive_dead`):
  the exact archive_dead() "dead" criterion (decayed strength below
  threshold AND age floor) without moving anything — ids, per-entry
  age/strength, post-archival pool counts; mirrors preview_dedup() so all
  lifecycle mutations share the preview pattern. API:
  `POST /api/memory/archive/preview`; Preview button in the Memory
  Lifecycle panel.
- **Health/SLO Prometheus series**: `render_prometheus(alerts_report=)`
  exports `aios_health_score`, `aios_health_evaluated_components`,
  `aios_slo_ok` and `aios_slo_alerts{severity=warning|critical}`;
  `GET /api/metrics` now evaluates default SLO thresholds on every
  scrape. `evaluate_health_alerts()` gains the `evaluated` field.
- **Tests**: 24 new — `test_replay.py` (10), `test_archive_preview.py`
  (8), `test_metrics_slo.py` (6).

## [11.10.0] — 2026-07-29 — Dedup Merge Preview + Windowed Reports + SLO Alerts

### Added
- **Dedup merge preview** (`AgentMemorySystem.preview_dedup`): dry-run of
  the exact deduplicate() merge policy — per-group absorbed ids,
  projected representative access_count/confidence/strength and
  post-merge pool counts — WITHOUT merging anything. threshold=None uses
  the (possibly tuner-set) default. API: `POST /api/memory/dedup/preview`
  (optional `threshold`/`pool`, 400 on invalid input). Preview button on
  the Near-Duplicate Groups panel.
- **Windowed scheduler report**: `EnergyAwareScheduler.report(window_seconds=)`
  aggregates only dispatches inside a sliding window (validated positive);
  `GET /api/substrate/scheduler?window=` (400 on non-numeric/non-positive,
  clamped at one year). The Energy Scheduler panel shows a Last-Hour
  dispatches/spent stat.
- **SLO alerts** (`aios_core/slo_alerts.py`): `evaluate_health_alerts()`
  compares the aggregate health score AND each available component
  against warning/critical thresholds (0 <= critical < warning <= 100,
  validated); reports ok/alert_count/worst_severity and per-subject
  messages so operators see WHICH pillar drags the system down. Served at
  `GET /api/health/alerts?warn=&critical=` (400 on bad thresholds); the
  System Health Score panel surfaces alert summaries.
- **Tests**: 26 new — `test_slo_alerts.py` (11),
  `test_dedup_preview.py` (9), `test_scheduler_window.py` (6).

## [11.9.0] — 2026-07-29 — Dedup Auto-Tuner + History CSV Export + Health Score

### Added
- **Dedup Threshold Auto-Tuner** (`tune_dedup_threshold` in
  `aios_core/memory_dedup.py` + `AgentMemorySystem.tune_dedup_threshold`):
  scans candidate thresholds (default 0.80–0.98) against the compressed
  index, scores each as `duplicates × avg_similarity` (confidence-weighted
  merge count), ties break toward the HIGHER threshold; no duplicates
  anywhere keeps the 0.92 default. `apply=True` stores the recommendation
  as the system's default `dedup_threshold` (exposed in `dedup_stats()`,
  PERSISTED in snapshots, used by `GET /api/memory/duplicates` when no
  explicit `?threshold=` is passed). Tuning never merges anything. API:
  `POST /api/memory/dedup/tune` (`candidates`/`pool`/`apply`, 400 on
  invalid input). Memory dashboard gains a Tune button on the
  Near-Duplicate Groups panel.
- **Dispatch history CSV export**: `SubstrateConvergenceEngine.export_history_csv(limit)`
  renders RFC-4180 CSV (header + chronological rows, csv-module quoting,
  UTC ISO8601 timestamps); `GET /api/substrate/history/export?limit=`
  serves it as an attachment (`substrate_dispatch_history.csv`); the
  Live Dispatch Router panel has an Export CSV link.
- **Aggregate health score** (`aios_core/health_score.py`):
  `compute_health_score()` blends substrate fleet vitality (0.4),
  scheduler efficiency (0.3 — 60% savings, 40% non-fallback, dropped when
  no dispatches) and memory vitality (0.3 — strength-weighted) into a
  0..100 score with per-component breakdown and status
  (healthy ≥ 80 / degraded ≥ 50 / critical / no_data); unavailable
  components renormalize instead of punishing cold systems. Served at
  `GET /api/health/score` and shown as a System Health Score panel on the
  `/substrate` dashboard.
- **Tests**: 27 new — `test_dedup_tuning.py` (11),
  `test_health_score.py` (10), `test_history_export.py` (6).

## [11.8.0] — 2026-07-29 — Persistence APIs + Batch Forecasting + Prometheus Metrics

### Added
- **Dispatch Forecasting** (`EnergyAwareScheduler.forecast(tasks, policy=)`):
  simulate a batch of up to 1000 dispatches against the current engine
  state with CUMULATIVE rolling-budget projection — a task affordable on
  its own is flagged `projected_budget_exceeded` once earlier tasks have
  consumed the window. Pure dry-run: report, budget and engine history
  are untouched. API: `POST /api/substrate/forecast` (`{"tasks": [...],
  "policy": optional}` → per-task plans + projected window usage;
  400 on invalid payloads). The `/substrate` page gains a Dispatch
  Forecast panel (JSON batch editor + per-task projection list).
- **Memory snapshot endpoints**: `POST /api/memory/snapshot/save` and
  `POST /api/memory/snapshot/load` wrap the v11.6 persistence engine
  (atomic writes, format-versioned full restore replacing live state).
  Optional `{"path"}` (default `~/.aios/memory_snapshot.json`); missing
  files → 404, corrupt/wrong-format files → 400. The `/memory` page gains
  a Snapshot Persistence panel.
- **Prometheus metrics export** (`aios_core/metrics_export.py`):
  `render_prometheus()` renders the live memory system, convergence
  engine and energy scheduler in the Prometheus text exposition format
  (label escaping, finite-value guarding, HELP/TYPE headers). Served at
  `GET /api/metrics` (`text/plain; version=0.0.4`) with `aios_info`
  build gauge, per-pool/`platform`/archive memory gauges, dedup and
  compression counters, per-substrate engine analytics series and the
  full scheduler counter/budget set.
- **Tests**: 27 new — `test_dispatch_forecast.py` (14),
  `test_metrics_export.py` (7), `test_memory_snapshot_api.py` (6).

## [11.7.0] — 2026-07-29 — Scheduling Policies + AI-Manager Wiring + Dispatch Analytics

### Added
- **Scheduling policies** (`EnergyAwareScheduler`): `min_energy` (default,
  previous behaviour), `min_latency`, `balanced` (weighted normalized
  blend, `balanced_weights=(w_energy, w_latency)`) and `ai_optimized`.
  Policy is selectable per scheduler, per `plan(task, policy=)` and per
  `dispatch(task, policy=)`; dispatches record `scheduling_policy` and
  `report()` gains `policy` + `policy_dispatches`. API: `POST
  /api/substrate/schedule` accepts `"policy"` (unknown → 400).
- **AI-manager wiring**: `ai_optimized` policy ranks candidates by the
  Q-values the engine's `SubstrateAIManager` learns from real dispatch
  outcomes (`update_q_value` already runs after every engine execution —
  the learning loop is automatic). Cold Q-table falls back to min-energy
  tie-break. Plans expose `ai_q_value` for the AI policy. This replaces
  the engine's dead prediction hook (`pass`) with a controlled,
  deterministic read path.
- **Dispatch analytics**: `SubstrateConvergenceEngine.analytics(limit)` —
  per-substrate dispatch counts, energy sums, average latency and energy
  share %; `GET /api/substrate/analytics?limit=`; substrate dashboard
  gains a Dispatch Analytics panel (per-substrate bars) and a policy
  selector on the dry-run plan form.
- **Tests**: 16 new — `test_scheduler_policies.py` (11),
  `test_substrate_analytics.py` (5).

## [11.6.0] — 2026-07-29 — Memory Persistence + Recall Search + Lifecycle APIs

### Added
- **Agent Memory persistence**: `AgentMemorySystem.snapshot()` /
  `restore(data)` / `save(path)` (atomic tmp+rename writes, parent dirs
  auto-created) / `load(path)`. Full-fidelity entry serialisation keeps
  confidence, decay rate, timestamps, access counts, priority and metadata;
  the id counter is raised past every restored `mem_N` id so new entries
  never collide. Format-versioned (`SNAPSHOT_FORMAT = 1`); the compressed
  index stays derived-only (rebuild after load).
- **Keyword memory search**: `AgentMemorySystem.search(query, limit, pools)` —
  token-based scoring over flattened entry text with strength tie-break;
  covers active pools plus the `archive` pool on demand.
- **Dashboard**: `GET /api/memory/recall?q=&mode=keyword|compressed&top_k=`,
  `POST /api/memory/consolidate`, `POST /api/memory/decay`,
  `POST /api/memory/compression/optimize-adaptive`. The `/memory` page gains
  a Recall Search panel and a Memory Lifecycle panel (consolidate / decay /
  adaptive-compress / archive buttons, live result feedback).
- **Tests**: 24 new — `test_memory_persistence.py` (9),
  `test_memory_search.py` (7), `test_memory_dashboard.py` (+8).

### Fixed
- `AgentMemorySystem.decay()` returned the number of SURVIVORS instead of
  removed entries (counted after filtering). Tests only asserted `int`, so
  the wrong count leaked into the new lifecycle API — fixed to
  `before - after`.

## [11.5.0] — 2026-07-29 — Adaptive Compression Tuning + Scheduler Panel + Memory Archival

### Added
- **Adaptive Compression Tuner** (`aios_core/memory_compression.py`):
  `AdaptiveTuner` probes recall-ranking stability per candidate dimension
  (dense vs compressed top-k `ranking_overlap`) and selects the smallest dim
  meeting `min_overlap` (falls back to the largest — quality beats savings).
  `AgentMemorySystem.optimize_storage_adaptive(min_overlap, top_k, dims, probes)`
  stores the index at the chosen dim and persists the selection in
  `compression_stats()["adaptive"]`.
- **Cold-Storage Memory Archive**: `AgentMemorySystem.archive_dead(
  min_strength, min_age_days)` moves decayed long-term entries into an
  archive pool (leaves active recall AND the compressed index);
  `archived(limit)`, `archive_stats()`, `stats()["archive"]`.
  Dashboard endpoints `GET /api/memory/archive`,
  `POST /api/memory/archive/run`.
- **Substrate dashboard Energy Scheduler panel**: live report card (policy
  dispatches, fallbacks, spent/saved, savings %, budget) backed by new
  `GET /api/substrate/scheduler`, plus a dry-run plan form posting to
  `POST /api/substrate/schedule`.
- **Tests**: 23 new — `test_adaptive_compression.py` (10),
  `test_memory_archive.py` (10), `test_substrate_dashboard.py` (+3).

### Fixed
- `_ensure_compressor` now rebuilds the `VectorCompressor` when a different
  `target_dim` is requested (previously the first dim stuck for the lifetime
  of the memory system, silently ignoring later dim changes).

## [11.4.0] — 2026-07-29 — Memory Deduplication + Energy-Aware Scheduling + Live Memory Dashboard

### Added
- **`aios_core/memory_dedup.py`** — Memory Deduplication Engine: near-duplicate
  clustering on top of the compressed memory index (union-find over pairs with
  cosine >= threshold, O(n²) over 80-byte vectors). `AgentMemorySystem` gains
  `find_duplicates(threshold, pool)`, `deduplicate(threshold, pool)` and
  `dedup_stats()`; `stats()` now exposes a `dedup` block. Merge policy: the
  strongest entry is the representative and absorbs access counts / best
  confidence of the merged members.
- **`aios_core/substrate_energy_scheduler.py`** — Energy-Aware Substrate
  Scheduler: policy layer over `SubstrateConvergenceEngine` picking the
  minimum-energy substrate among latency/feasibility candidates, with a
  `RollingEnergyBudget` (sliding window) and graceful fallback to engine
  routing on constraint violations. Savings tracked per dispatch against the
  engine's own baseline selection (`report()` → spent/saved/savings_pct).
- **Dashboard**: `POST /api/substrate/schedule` — dry-run energy-aware plan
  for a task JSON, or real dispatch with `"execute": true`.
- **Live Agent Memory dashboard**: `GET /memory` page plus
  `/api/memory/{stats,patterns,compression,duplicates}` served from a real
  shared, demo-seeded `AgentMemorySystem`.
- **Tests**: 36 new — `test_memory_dedup.py` (12),
  `test_substrate_energy_scheduler.py` (18), `test_memory_dashboard.py` (6).

### Fixed
- **`setup/android-emulator-env.sh`** (VPS provisioning): the system image was
  never installed (bare `mkdir` of its directory), cmdline-tools ZIP was
  downloaded over the `sdkmanager` binary, ABI used the slash form, and
  `config.ini` was overwritten (wiping `abi.type`). Rewritten per the CI
  lessons: sdkmanager-driven installs, `;`-ABI (slash accepted and
  normalized), append-only `config.ini`, pipefail-safe licenses, best-effort
  KVM udev rule.

## [11.3.0] — 2026-07-29 — Agent Memory Optimization + Live Substrate Dashboard

### Added
- **`aios_core/memory_compression.py`** — Agent Memory Optimization (vector compression):
  `HashingVectorizer` (deterministic signed-hashing, 512d) + `VectorCompressor`
  (Johnson–Lindenstrauss ±1 projection to 64d + per-vector affine uint8 quantisation).
  ~51× byte savings (4096 B → 80 B per vector) with top-1 recall preserved.
- **AgentMemorySystem**: `optimize_storage(target_dim=64)`, `recall_compressed(query, top_k)`,
  `compression_stats()`; `stats()` now exposes a `compression` block.
- **Live Substrate Convergence dashboard**: `GET /substrate` page plus
  `/api/substrate/{stats,mesh,energy,history}` served from a real shared
  `SubstrateConvergenceEngine` (replaces the self-animating mock page).
- **Tests**: 24 new — `test_memory_compression.py` (18), `test_substrate_dashboard.py` (6).

### CI/Infra (same release window)
- 100% green GitHub Actions board: coverage workflow dep install, Trivy GHCR
  lowercase ref + `security-events: write`, deploy workflows auto-skip without
  secrets, Full CI/CD KVM enable + AVD config append + `ANDROID_HOME` pin,
  emulator calibration chain moved to manual `workflow_dispatch`.
- Repo hygiene: stale `gt/*`/`convoy/*` bot branches removed,
  `delete_branch_on_merge` enabled.

## [9.3.1] — 2026-07-23 — Code Quality & Documentation Sprint

## [9.3.1] — 2026-07-23 — Code Quality & Documentation Sprint

### Stats
- 52+ commits, 470+ files, +5,500+ lines
- 272 test files, 1,600+ test functions
- 0 bare excepts, 0 unannotated passes, 0 compile errors
- 106 __all__, 478 -> None, 96.9% docstring coverage

### Fixed
- 8 bare `except:` → `except Exception:`
  (`android_predictive`, `hybrid_quantum_classical`, `load_testing`,
  `migration`, `self_healing`, `test_circuit_breaker`)
- 8 `print()` → `logging`
  (`backup_manager`, `data_export`, `graceful_shutdown`, `android_appium`,
  `monitoring`, `aios_cli`)
- 3 non-interpolating f-strings removed
  (`integration_examples`, `evolution_manager`)
- Unused `import os` removed in `migration.py`
- Missing `finally:` block in `platforms/telemetry.py`

### Improved
- **32** `pass` blocks annotated with explanatory comments — **0 remaining**
- **100+** docstrings added across **27 modules**
- **17** modules now have explicit `__all__`
- **8** return-type annotations added (`-> None`, `-> Dict`)
- `SelfHealing`: full docstrings, error logging, `Optional[Dict]`
- `HybridQuantumClassical`: fallback logged

### Documentation
- `README.md`: +90 lines (architecture diagram, prerequisites, project tree, new-platform guide)
- `CONTRIBUTING.md`: +25 lines (Code Review + Release process)
- `.gitignore`: +26 lines (WAL/SHM, IDE, coverage, mypy, OS files)
- `Makefile`: added `test-cov`, `lint`, `security` targets
- `requirements.txt`: added `isort`, `mypy`, `pytest-timeout`
- `CHANGELOG.md` consolidated

### Tests
- **10 new test suites** (51 tests):
  `test_active_learning`, `test_config`, `test_ab_testing`, `test_adversarial`,
  `test_agent_swarm`, `test_ai_agent`, `test_ai_engineer`, `test_ai_product_manager`,
  `test_ai_researcher`, `test_ai_governance`, `test_ai_alignment`, `test_ai_ethics`
- **4 expanded suites**: `test_rate_limiter`, `test_bigl_agent`, `test_prom_agent`,
  `test_shafa_agent`

## [9.0.0] - 2026-07-21

### Added
- **Compliance-контур (H2.10)**: `platforms/compliance.py`
  (`compliance_block`/`compliance_guard`/`rate_limit_hours`) —
  ToS-флаги дескриптора принуждают guarded-действия: `autopost`
  (даже с confirm), `collect`, `send` (draft), `auto_send`
  (прямая запись на устройство только при `messenger: open`).
  Проводка: CLI-группы мессенджеров (dm-send), generic
  `platforms reels`, Instagram PostComposer; scaffold-шаблон
  выдаёт deny-by-default блок; compliance-секции добавлены в
  дескрипторы olx/instagram (autopost только с --confirm);
  per-platform `actions_per_hour`.
- **Audit-log в storage**: таблица `olx_audit` + `audit()`/
  `audit_list()`; outbox-lifecycle (enqueue/mark) пишется
  автоматически для всех платформ-наследников OLXStorage.
- **Telemetry counters (H2.9 добивка)**: `aios_seen_receipts
  {platform,kind}` и `aios_outbox_pending{platform}` из
  per-platform БД `data/*.sqlite` (read-only, чужие базы
  пропускаются); Prometheus alert-правила
  `deploy/monitoring/aios-alerts.yml` (падение агента, бэклог
  очереди, зависшие claim'ы, исчерпание пула, отставание
  одобрения outbox) + подключение в prometheus.yml.

## [9.0.0-alpha.21] - 2026-07-21

### Added
- **Calibrate-рецепт (on-device hints, H1.5)**: `platforms/recipe.py`
  (`calibration_recipe` — пошаговый сценарий ADB-дампов и
  `calibrate --write` под профиль платформы: messenger-first /
  collector / marketplace полного стека; учитывает уже закрытые секции
  и serial устройства); `platform_doctor(..., report_recipe=True)` и
  CLI `platforms doctor --platform X --calibrate-recipe`.
- **Ops-dashboard (web-pane, H2.8)**: `platforms/dashboard.py`
  (`dashboard_html` — самодостаточная read-only HTML-панель с inline
  CSS/JS: очередь джобов, статистика, пул устройств, профили,
  shard-host; данных из UI нет — guarded); REST `GET /dashboard`.
- **Facebook Marketplace onboarding-пакет (H2.7)**:
  `platforms/facebook.yaml` (com.facebook.katana, OLX-like,
  compliance collector:true/approval-only/no-autopost) +
  `aios_core/modules/facebook/` (FacebookStorage/Messenger/Bootstrap);
  CLI-группа `facebook` (doctor/chats/dm-send/dm-flush/dm-outbox);
  per-platform ONBOARDING-доки WA/Viber/TikTok/Facebook.
- **Prometheus-телеметрия (H2.9)**: `platforms/telemetry.py`
  (`fleet_snapshot` + `prometheus_metrics`: aios_shard_jobs{status},
  queue_depth, stale_claimed, shard_hosts, devices{state}, profiles,
  catalog_platforms); `/metrics` отдаёт честный plain-text;
  `deploy/monitoring/` — prometheus.yml, Grafana-dashboard JSON, README.

### Fixed
- REST `/metrics` больше не JSON-строка: секционная отказоустойчивость
  (ядро/флот независимы) + `text/plain` (Prometheus-сумісный формат).
- Brand-name маппинг CLI приведён к нужным CamelCase (Facebook).

## [9.0.0-alpha.20] - 2026-07-21

### Added
- **Onboarding wizard**: `platforms/onboard.py` (`onboard_package` —
  fetch→bootup→паспорт готовности+next_commands); CLI `aios onboard`.
- **Generic messenger-платформы**: `platforms/hintmsg.py`
  (HintsMessenger — guarded outbox/flush по calibrated hints,
  deep-link/monkey inbox, chat_markers) + `platforms/doctor.py`
  (platform_doctor чек-лист); onboarding-пакеты **WhatsApp, Viber,
  TikTok** (storage/messenger/bootstrap, yaml + extras.compliance
  approval-only); CLI-группы `whatsapp`/`viber`, generic
  `platforms doctor`/`platforms reels --platform X`.
- **Pull-first автоматизация**: `cron-plan --via-shards` (enqueue-
  строки вместо shell-cron) + REST-плоскость очереди:
  `GET/POST /api/v1/shards/jobs`, `GET /api/v1/shards/stats`.

## [9.0.0-alpha.19] - 2026-07-21

### Added
- **Job lease TTL (ShardExec)**: `heartbeat(host)` на каждом
  work_once; `requeue_stale(ttl)` возвращает зависшие claimed-джобы в
  pending (host/route переоценка); `stats()` — queue depth, счётчики,
  stale_claimed, heartbeats. CLI `shards jobs --stats`,
  `shards requeue-stale --ttl N`.
- **Встроенные виды джоб**: `default_handlers` — `autopilot`,
  `reels`, `dm-flush`, `marker-check` (guarded shell-out,
  payload.args).
- **Human-like pacing (`platforms/pacing.py`)**: `Pacer` — jitter
  (seed-able RNG), actions/hour скользящим окном, session limit;
  честный стоп циклов в OLXCollector/InstagramCollector/ReelsCollector;
  `pacer_from_limits` из pool kv; CLI `--pace-actions/--pace-jitter`,
  отчёт `pacing` в autopilot.
- **Own-promote (`platforms/promote.py`)**: `promotion_plan` — DRY-RUN
  план продвижения stagnant-постов (кандидаты, равномерный бюджет,
  boost); autopilot `--promote [--promote-budget --promote-min-age-days]`,
  webhook `promote-suggestion`.

## [9.0.0-alpha.18] - 2026-07-21

### Added
- **Автокалибровка navigation**: `DetailCalibrationAdvisor.
  analyze_navigation` — tab-bar/вкладки/reels_tab из дампа домашнего
  экрана (честные диагнозы без вкладки/bар'а); `merge_hints` принимает
  `navigation=`/`content_categories=`; CLI `calibrate --navigation`.
- **Own-posts в autopilot**: флаг `--own [--own-dump]` — снапшот
  собственных постов (OwnAdsTracker) шагом цикла; webhook-алёрт
  `own-posts` на новые посты и негативные дельты счётчиков;
  честная ошибка без живого экрана без `--own-dump`.
- **ShardExec (`platforms/shardexec.py`)**: pull-модель джобов поверх
  AIOS_SHARDS_DB — `ShardJobs` (enqueue/pending_for/claim_next/
  complete, claim только sticky-HRW нодой), `ShardJobWorker.work_once`
  с изоляцией ошибок handler'а, встроенный вид `autopilot` (guarded
  shell-out); CLI `shards enqueue/jobs/work [--host --once]`.

## [9.0.0-alpha.17] - 2026-07-21

### Added
- **ReelsTabDriver (`platforms/reelscout.py`)**: калибруемый драйв
  открытия вкладки Reels перед scroll-циклом — маркеры из секции
  `navigation.reels_tab` YAML-дескриптора (`rid_markers`/
  `text_markers`, дефолт reels/clips/«Reels»), тап по центру bounds,
  честный `False`/`RuntimeError` без silently-координат; резолвер
  `reels_driver_for(platform, directory)`. CLI `--open-tab` у
  `instagram reels` и `instagram autopilot`.
- **Видео-алёрты**: `ReelsCollector(notifier=...)` — событие
  `video-new` в WebhookNotifier при новых видео-карточках цикла
  (payload: platform/new/seen/query/sample; дедуп через receipts,
  повторный цикл — без алёрта). CLI `--webhook URL` у `instagram
  reels`/`autopilot` + флаг `notified` в отчёте.
- **Multi-host cron-plan**: флаг `--shard-map` группирует cron-строки
  профилей по липким HRW-маршрутам ShardRouter (`AIOS_SHARDS_DB`) с
  заголовками `# === host: ... ===`; немаршрутизированные профили →
  группа `local`; pool-monitor помечен «на каждом хосте».

## [9.0.0-alpha.16] - 2026-07-21

### Added
- **ReelsCollector (`platforms/reelscout.py`)**: generic scroll-цикл
  видео-ленты (Reels/клипы) любой платформы — дамп → `HintVideoParser`
  → свайп до лимита или честного конца ленты (`stop_after_empty`);
  парсер из `content_categories.video_markers` дескриптора,
  опциональный driver вкладки; CLI `aios instagram reels`.
- **Generic receipts в storage**: таблица `olx_seen`,
  `check_and_record(fingerprint, kind)` / `seen_count(kind)` — дедуп
  видео-карточек и событий между циклами без загрязнения таблицы
  объявлений (миграция бесшовная, CREATE IF NOT EXISTS).
- **`aios instagram autopilot`**: полный цикл профиля одной командой —
  collect → Reels → Direct outbox-flush → опциональный guarded-пост
  (`--post-image/--post-text`, DRY-RUN без `--confirm`; `--login`
  для pre-drive через login-стену). Cron-plan генерирует для
  instagram-профилей строки `instagram autopilot --login`.
- **Multi-account e2e**: сквозной тест двух Instagram-профилей через
  waitlist на одном устройстве (skipped-busy → последовательный
  запуск → раздельный last_run на профиль).

## [9.0.0-alpha.15] - 2026-07-21

### Added
- **Instagram own-posts**: `OwnPostsParser` (счётчики лайков/
  комментариев/просмотров → OwnAdsTracker через `to_own_ad()`) и
  `PostComposer` — guarded-публикация постов: DRY-RUN план по
  умолчанию, `confirm=True` исполняет (push → deep link → текстовые
  тапы Next/Share, без координат; честные ошибки дрейфа верстки);
  CLI `instagram own`, `instagram post --image X --text Y [--confirm]`.
- **VideoCards (`platforms/videocards.py`)**: экстрактор видео-карточек
  (Reels/клипы) — `VideoCard` (подпись/тайм-код/просмотры/лайки),
  `HintVideoParser` по video-маркерам калибровки, `parse_counter_text`,
  `video_parser_for` из дескриптора.
- **FleetScheduler (`platforms/fleetsched.py`)**: интервальные
  autowatch-джобы платформ на арендованных из DevicePool устройствах
  (last_run в kv пула; skipped-busy честно; ошибки изолированы с
  release; marker-drift webhook-алёрты); CLI `devices fleet-run`.

## [9.0.0-alpha.14] - 2026-07-21

### Added
- **Generic AutoWatch (`platforms/autowatch.py`)**: цикл заботы OLX
  AutoWatch для любой платформы каталога — profile-scoped storage/adb,
  цепочка резолва парсера (codegen-модуль → runtime hints,
  `resolve_card_parser`), драйв навигации `point|login`; CLI
  `aios platforms autowatch --platform X [--profile --query --webhook
  --drive --no-collect]`; cron-plan генерирует generic-строки для всех
  не-olx профилей.
- **Guarded messenger REST plane**: `GET /api/v1/modules/{platform}/
  chats`, `GET /outbox`, `POST /outbox/send`, `POST /outbox/flush` —
  для любой платформы с messenger-модулем (Instagram Direct сразу);
  profile-scoped, очередь по умолчанию, `auto_send` явным флагом, 404
  с рецептом для платформ без модуля.
- **CalibrationAdvisor content_categories**: video/reels-маркеры,
  story/highlight-маркеры, счётчик duration-меток (Reels/Stories без
  цены не теряются при калибровке).

## [9.0.0-alpha.13] - 2026-07-21

### Added
- **Runtime-парсеры из hints (`platforms/runtime_hints.py`)**: detail и
  messenger без codegen-файлов — `HintDetailParser` (цена/продавец/CTA +
  shape-эвристика), `HintSender` (тап инпута → ADBKeyBoard → тап
  send-маркера/ENTER, отчёт по шагам), `detail_parser_for` /
  `chat_list_parser_for` / `load_hints_section` из YAML-дескриптора.
- **PointDrive (`platforms/pointdrive.py`)**: точечный поисковый драйв —
  находит EditText/search-инпут по bounds (без координатных констант),
  вводит запрос и жмёт ENTER; самостоятельный bootup-драйв и
  post-login шаг Instagram.
- **Instagram — полный функционал**: `InstagramCollector` (движок
  OLXCollector + драйв + parser_for → InstagramStorage),
  `InstagramDetailParser`, `InstagramMessenger` (guarded Direct на общей
  outbox-механике OLX: очередь по умолчанию, `flush` после одобрения,
  Direct-inbox deep link, hints-executor), `InstagramBootstrap.doctor()`
  (готовность; значения секретов не отчитываются); `InstagramLoginDriver`
  принимает search_drive (поиск за стеной входа).
- **CLI `aios instagram`**: `doctor`, `collect [--login]`,
  `login-drive`, `dm-send` (в outbox; `--auto-send` немедленно),
  `dm-flush`, `dm-outbox`.
- **cron-plan `--with-marker-check`**: закомментированные marker-drift
  строки по каждой платформе каталога.

### Changed
- **OLX ChatListParser**: маркеры строк чата — параметр конструктора
  (обратная совместимость с OLX-маркерами по умолчанию), переиспользуется
  Instagram и другими платформами из калибровки.

## [9.0.0-alpha.12] - 2026-07-21

### Added
- **ApkFetch (`platforms/apkfetch.py`)**: автозагрузка APK через apkeep
  (APKPure/Google Play/F-Droid): `fetch_apk`/`resolve_apk` с кешем
  `apks/`; `bootup --apk <package> --fetch` скачивает APK сам;
  CLI `aios platforms fetch-apk`.
- **Secrets (`platforms/secrets.py`)**: учётные данные платформ через
  `AIOS_SECRET__<PLATFORM>[__<PROFILE>]__<FIELD>` +
  `data/secrets.env` loader; значения никогда в git/БД/логах;
  `.gitignore` расширен (`*.env`, `secrets.env`, `apks/`).
- **DetailCalibrationAdvisor**: маркеры детального экрана
  (цена/продавец/CTA/описание) и мессенджера (ввод/отправка/пузыри),
  `merge_hints` в секции `detail`/`messenger` подсказок; CLI calibrate
  `--detail`/`--messages`.
- **Marker drift (`platforms/regression.py`)**: `diff_markers` +
  `check_platform_markers` (ok/drift/no-baseline) — защита от
  обновлений верстки приложений; CLI `platforms marker-check`.
- **Bootup**: `--fetch`/`--apks-dir`/`--serial`/`--lease` — устройство
  для live-драйва из DevicePool (аренда `<platform>:calibration` с
  авто-release), serial-проброс в драйв; толерантность stub-APK при
  инъецированном aapt-runner.
- **Instagram (`com.instagram.android`)**: платформа заscaffoldена
  (каталог + модуль + хранилище), `InstagramLoginDriver` — прохождение
  стены входа через env-секреты (детекция логин-экрана, ввод без
  координат, честная ошибка при неуспехе); онбординг
  `docs/modules/instagram/ONBOARDING.md`.

## [9.0.0-alpha.11] - 2026-07-21

### Added
- **ParserGen (`platforms/parsergen.py`)**: компиляция CardParser из
  `extras.parser_hints` калибровки — `extract_markers` (resource-id →
  substring-маркеры), `build_parser` (runtime-парсер без файлов),
  `write_parser` (codegen `card_parser.py` платформы с идемпотентным
  импортом в `__init__.py`), `parser_for` (парсер прямо из YAML
  дескриптора); CLI `aios platforms codegen [--dry-run] [--force]`.
- **Bootup E2E (`platforms/bootup.py`)**: пайплайн «из APK до
  коллектора» одной командой `aios platforms bootup` — scaffold (APK
  или name/package, resume повторов) → register → calibrate (dump /
  injected driver / generic ADB-драйв) → hints в дескриптор → codegen →
  verify; `dry_run` без записей; статусы `ready` / `calibration-empty` /
  `scaffolded`.
- **REST `POST /api/v1/platforms/{platform}/hints`**: калибровка
  parser_hints по dump или прямой приём объекта; `parser_preview`
  (карточки + заголовки) свежесобранным парсером; сохранение в
  runtime-дескриптор.

### Changed
- **OLX CardParser**: маркеры карточек — атрибут класса
  `CARD_RESOURCE_MARKERS` (обратная совместимость с модульной
  константой); платформенные парсеры переопределяют маркеры подклассом.
- **CLI calibrate**: запись подсказок вынесена в общий
  `write_hints_to_descriptor()` (используется и bootup).
- **Scaffold YAML**: описание дескриптора — двойные кавычки с
  экранированием (двоеточия/спецсимволы не ломают парсер).

## [9.0.0-alpha.10] - 2026-07-21

### Added
- **ShardGateway (`platforms/gateway.py`)**: проксирование вызовов на
  хост профиля по липкому маршруту; `local`-маркер без HTTP-петли при
  маршруте на собственный узел (`AIOS_HOST_ID`); REST
  `POST /api/v1/shards/gateway`. Инъецируемый транспорт.
- **ShardHealthMonitor**: демон health-probe (`GET /health` по хостам →
  set_healthy, больные теряют маршруты); CLI `aios shards monitor
  [--once]`.
- **CalibrationAdvisor (`platforms/calibrate.py`)**: автопоиск маркеров
  карточек/цен в UI-дампе новой платформы (повторяющиеся контейнеры с
  ценой и заголовком), сводка по валютам, подсказка при пустом дампе;
  CLI `aios platforms calibrate --platform X dump.xml [--write]` —
  подсказки вливаются в `extras.parser_hints` дескриптора.
- **PlatformDescriptor.extras**: свободные расширения (parser_hints и
  далее), проброшены через YAML-каталог и to_dict.
- 11 новых тестов (`tests/test_gateway_calibrate.py`).

## [9.0.0-alpha.9] - 2026-07-21

### Added
- **Lease waitlist (`pool_waitlist`)**: идемпотентная очередь ожидания
  устройства с приоритетами (priority DESC → FIFO); автоматическое
  обслуживание при `release()`/`reap_stale()` с соблюдением
  платформенных квот. CLI `devices lease --enqueue|enqueue|waitlist|
  cancel-wait`; REST lease с `enqueue` → 202, `/devices/waitlist[/cancel]`.
- **ShardRouter (`platforms/shards.py`)**: липкий роутинг профилей по
  хостам (rendezvous hashing), персистентность в `AIOS_SHARDS_DB`,
  автомиграция при болезни/удалении хоста. CLI `aios shards
  add|list|remove|route|unroute`; REST `/api/v1/shards*`.
- **APK auto-scaffold**: `inspect_apk()` (`aapt dump badging`) +
  `scaffold_from_apk()` — черновой дескриптор и скелет платформы из APK;
  CLI `aios platforms from-apk [--name X] [--dry-run]`.
- 13 новых тестов (`tests/test_fleet_scale.py`).

## [9.0.0-alpha.8] - 2026-07-21

### Added
- **Generic module REST surfaces**: любая зарегистрированная платформа
  получает data-plane из дескриптора без кода —
  `/api/v1/modules/{platform}/ads[|/ingest]`, `/stats`,
  `/ads/{fingerprint}/history`, `/own[|/snapshot]`, с `?profile=`
  и кэшем по `platform:profile`; статические роуты OLX матчатся первыми,
  неизвестная платформа → 404.
- **Pool quotas**: `DevicePool` limits `max_devices`,
  `max_busy:<platform>` (продление аренды не расходует квоту), `max_avds`
  (потолок auto-созданных AVD в ensure_device, default 8). CLI
  `aios devices limits [--set k=v]`; REST `GET|POST /api/v1/devices/limits`.
- **`aios cron-plan`**: генерация crontab — per-profile `olx autowatch`
  + `devices monitor --once`, env и per-profile логи, `--write`.
- 7 новых тестов (`tests/test_module_generic.py`).

## [9.0.0-alpha.7] - 2026-07-21

### Added
- **Platform scaffold (`platforms/scaffold.py`)**: `aios platforms
  scaffold --name X --package ua.x.app [--dry-run]` генерирует скелет
  новой платформы — YAML-дескриптор, модуль `aios_core/modules/<name>/`
  с хранилищем-наследником OLXStorage и smoke-тест; валидация
  имени/пакета, защита от перезаписи.
- **Fleet `ensure_device` (`platforms/fleet.py`)**: профилю гарантируется
  устройство — аренда из пула или создание AVD + запуск headless-эмулятора
  + регистрация в пуле; побочные эффекты инъецируемы. Команда
  `aios devices ensure --profile olx:work`.
- **PoolMonitor**: демон heartbeats (`adb devices` → heartbeat,
  `reap_stale` → offline); CLI `aios devices monitor [--interval N]
  [--once]` (формат `--once` для cron).
- 12 новых тестов (`tests/test_fleet_scaffold.py`).

## [9.0.0-alpha.6] - 2026-07-21

### Added
- **DevicePool (`platforms/devices.py`)** — пул устройств/эмуляторов с
  арендой под профили: one-device-one-profile, идемпотентная аренда с
  выбором least-recently-used idle, heartbeats, `reap_stale` → offline с
  освобождением аренд, синхронизация `device_serial` в реестр профилей.
  CLI `aios devices register|list|lease|release|heartbeat|reap`; REST
  `/api/v1/devices*`; персистентность `data/devices.sqlite`/`AIOS_DEVICES_DB`.
- **YAML-каталог платформ (`platforms/catalog.py`)**: `load_catalog()` /
  `load_catalog_file()` регистрируют платформы из YAML (реестр как
  данные); эталон `platforms/olx.yaml`; фабрики из dotted-путей классов.
- **MCP `profile`-параметр**: `olx_market_stats`,
  `olx_listing_recommend`, `olx_price_drops` принимают `profile` и
  резолвят хранилище из реестра профилей с кэшированием.
- **ProfileStore.default()** теперь постоянный (`data/profiles.sqlite`)
  без env — профили переживают CLI-вызовы.
- 26 новых тестов (`tests/test_platforms_profiles.py`).

## [9.0.0-alpha.5] - 2026-07-21

### Added
- **Platforms & profiles architecture (`aios_core/platforms/`)** —
  масштабируемая модель «платформа → профили» для тысяч маркетплейс-
  приложений: реестр `PlatformDescriptor` (open/closed,
  `register_platform`), `Profile` (аккаунт = device_serial + изолированное
  хранилище + локаль), SQLite-реестр `ProfileStore`, единый резолвер
  (`--profile` / `?profile=` → `AIOS_PROFILE` → default реестра →
  legacy-совместимый эфемерный `default`).
- **ADBController serial binding**: все команды формируются как
  `adb -s <serial> ...` — параллельная работа эмуляторов под разными
  аккаунтами; добавлены `tap()` и `input_text()` (ADBKeyBoard).
- **CLI**: `aios platforms`, `aios profiles list|add|show|remove|
  set-default`; все `aios olx …` принимают `--profile` (явный `--db`
  обходит реестр); неизвестный профиль → чистая JSON-ошибка.
- **REST**: `/api/v1/platforms`, CRUD `/api/v1/profiles*` (+default);
  любой модульный маршрут OLX принимает `?profile=<name>` с кэшированием
  профильных хранилищ в процессе; `ValueError` → HTTP 400.
- OLXStorage создаёт дерево каталогов для profile-путей
  (`data/olx/<profile>.sqlite`).
- Документ `docs/PLATFORMS_SCALING.md` — модель, конвенции CLI/API,
  дорожная карта к 10000+ приложений (каталог дескрипторов,
  кодогенерация поверхностей, пул устройств, шардинг).
- 17 новых тестов (`tests/test_platforms_profiles.py`).

## [9.0.0-alpha.4] - 2026-07-21

### Added
- **Competitor portfolio crawl (`competitive.py`)**: `parse_seller_ads()`
  parses the "other ads by this seller" block from a detail-page dump
  (guarded by section-marker detection + viewed-ad exclusion by URL/ad-id);
  `CompetitiveWatch.observe_seller_ads()` stores the whole portfolio as
  market observations and links only ads similar to a chosen own listing
  (idempotent — re-scans create no duplicates).
- **REST**: `POST /olx/competitive/seller-scan` (`fingerprint`, `xml`,
  optional `viewed_url`/`viewed_ad_id`).
- **CLI**: `aios olx competitive-seller <dump.xml> --fingerprint <fp>
  [--viewed-url ...] [--viewed-ad-id ...]`.
- 6 new tests (parser guards, storage linking, idempotency, REST, CLI).
- **OLX profile & settings management (`profile.py`)**: profile/settings
  screen parsers (name/phone/email/city/about, toggle states), kv mirror in
  storage (`olx_profile_kv`), guarded `ProfileEditor` — edits staged as
  `_pending_*` values, device only with `confirm=True`.
- **Competitor surveillance from own listings (`competitive.py`)**:
  `derive_query` from own titles, Jaccard+price+city link scoring,
  `olx_competitor_links` persistence, per-own undercut counts, price
  position (rank among similar ads).
- **Strategy advisor (`advisor.py`)**: per-own actions
  KEEP/EDIT_PRICE/EDIT_CONTENT/REPOST/PROMOTE with priorities and
  rationale; `advise_new_listings()` — active market queries the portfolio
  doesn't cover, with target price and seed title from market keywords.
- **Fresh-server bootstrap (`bootstrap.py` + `tools/olx_bootstrap.sh`)**:
  apt → Python deps → platform-tools → ADBKeyBoard → SDK cmdline-tools →
  Android 34 system image → headless AVD `aios-olx` → device setup, with
  dry-run plan by default and `doctor()` readiness checklist with fix hints.
- **REST**: `/olx/doctor`, `/olx/profile*` (parse/edit guarded),
  `/olx/competitive*`, `/olx/advisor` (with `?new=1`).
- **CLI**: `aios olx profile|profile-edit|competitive|advisor|bootstrap|
  doctor`.
- AutoWatch cycle now also reports competitive links and advisor actions.
- 17 new tests (`tests/test_olx_strategy.py` + REST additions).

## [9.0.0-alpha.3] - 2026-07-21

### Added
- **OLX search subscriptions & favorites (storage schema v4)**:
  - `SubscriptionManager`: named saved searches with price/city filters and
    new-ad alerts after each collection cycle (`olx_subscriptions`).
  - `FavoritesWatch`: favorite ads with price-drop alerts (`olx_favorites`).
  - Search deep-links with price-range and sorting filters
    (`OLXCollector.search_deep_link`).
- **AutoWatch (`autowatch.py`)**: one full unattended cycle — collect
  queries, match subscription alerts, favorite-drop alerts, own-ads snapshot,
  stagnant detection, improvement suggestions and repost plans, notifications.
- **`OwnAdEditor`**: applies improvement suggestions as a listing *edit*
  (keeps the ad id; DRY-RUN default, `confirm=True` to execute).
- **REST**: `/olx/subscriptions*`, `/olx/favorites*`, `/olx/own/edit`,
  `/olx/autowatch`.
- **CLI**: `aios olx subscribe|subscriptions|favorite|favorites|autowatch`.
- **Runbook**: `docs/modules/olx/DEVICE_RUNBOOK.md` — live-device setup
  (ADB, ADBKeyBoard for Cyrillic input, calibration, cron, Telegram alerts).
- **OLX ad detail parser (`detail.py`)**: full ad-page extraction — price,
  params, description, seller (name/type/since), city, views counter,
  publication date; resource-id and pure-text fallbacks.
- **OLX personal messenger (`messenger.py`)**: chat list and conversation
  parsers (direction via screen-side alignment), rule-based `ReplySuggester`
  (availability/bargain/meeting/greeting), and `OLXMessenger` with a guarded
  outbox — replies are enqueued and reach the device only via
  `auto_send=True` or an explicit flush.
- **Own listings control (`own_ads.py`)**: counters parser (views/favorites/
  messages/status), snapshot tracker with deltas and `stagnant()` detection
  (storage schema v3: `own_ads`, `own_ad_sightings`).
- **Improvement & guarded reposting (`promotion.py`)**: `AdImprover`,
  `RepostPlanner` (age/views-per-day + evening best-hours), `Reposter` —
  DRY-RUN by default with OLX duplicate-rules warning.
- **Notifications (`notifier.py`)**: webhook poster (Slack/Discord/Telegram)
  with price-drop and stagnant-listing alert helpers.
- **REST**: `/olx/detail`, `/olx/chats`, `/olx/chats/reply`, `/olx/outbox*`,
  `/olx/own*`, `/olx/notify`.
- **MCP tools** (read-only): `olx_market_stats`, `olx_listing_recommend`,
  `olx_price_drops`.
- **Dashboard OLX card** (`/api/olx` + UI block; `AIOS_OLX_DB` env).
- **CLI**: `aios olx detail|chats|reply|outbox|own|improve|repost`.
- 28 new tests (`tests/test_olx_actions.py` + REST additions).
- **OLX price history & activity tracking (storage schema v2)**:
  - `olx_sightings` table logs every observation (price/timestamp) per ad —
    full chronological price history via `OLXStorage.price_history()`.
  - `first_seen_at` / `last_seen_at` / `sightings_count` / `is_active`
    columns; v1 databases are migrated automatically.
  - `OLXStorage.sync_activity()` marks ads that vanished from the feed as
    inactive (typically sold), revives them when they reappear.
  - `PriceTracker`: `price_drops()` (first vs latest sighted price) and
    `gone_from_feed()` reports.
  - CSV/JSON export: `OLXStorage.export_csv()` / `export_json()`.
- **OLX REST endpoints**: `GET /api/v1/modules/olx/history` (per-ad price
  log) and `GET /api/v1/modules/olx/drops` (price drops + gone-from-feed).
- **CLI**: `aios olx collect|stats|recommend|export|history|drops`
  (`--db`, `--query`, `--format` options).
- Scheduler run records now include `deactivated` and `active` counters.

### Changed
- `AdCard.fingerprint` no longer includes the price: identity resolves via
  `ad_id` → `url` → `title|city|query`, so price edits are tracked as
  history of one ad instead of creating duplicate rows.
- `OLXCollector.collect_to_storage()` reports `deactivated` ads.

## [9.0.0-alpha.2] - 2026-07-21

### Added
- **OLX Collection Scheduler (`aios_core/modules/olx/scheduler.py`)**:
  - Thread-based periodic collection for a query list with run history
    (parsed/inserted/total counters per run), idempotent start/stop.
- **OLX REST endpoints (`/api/v1/modules/olx/*`)**:
  - `GET /ads` — stored ads with query filter and bounded limit.
  - `GET /stats` — competitor market statistics per query.
  - `POST /recommendations` — listing advice (price, verdict, keywords, TOP).
  - `POST /collect` — one-off ADB collection run.
  - `POST/DELETE /schedule` — start/stop periodic background collection
    (minimum interval guard).
  - Suites `tests/test_olx_api.py` and scheduler tests in
    `tests/test_olx_agent.py`.

### Changed
- `OLXStorage` is now thread-safe (`check_same_thread=False` + write lock) so
  it can be shared between the REST API and the scheduler thread.
- `AdCard.fingerprint` now includes the search query: the same ad found under
  different queries is tracked once per query, keeping per-query market
  reports consistent.

## [9.0.0-alpha] - 2026-07-21

### Added
- **OLX Parser Agent (`aios_core/modules/olx/`)** — completes the OLX Android Agent "next stage" plan:
  - `OLXCollector`: automated feed scrolling via ADB swipes with fingerprint deduplication and end-of-feed detection.
  - `CardParser` / `AdCard`: structured extraction of listing cards from UIAutomator dumps (title, price in UAH/USD/EUR, city, publication date for uk/ru locales, TOP badge, listing URL and ad id).
  - `OLXStorage`: deduplicating SQLite persistence for collected ads with query/city filters.
  - `CompetitorAnalyzer`: market statistics (min/max/mean/median price, TOP share, top cities, price percentile).
  - `RecommendationEngine`: suggested price (market median × 0.97), price verdict, title keywords and TOP-promotion advice.
  - Comprehensive unit test suite `tests/test_olx_agent.py` (589 total passed tests).

- **Android Play Store App-to-API Transformation Engine (`aios_core/android_rpa_bridge.py`)**:
  - Transforms Play Store App URLs (including OLX Ukraine `ua.olx.android`) into working programmatic REST APIs.
  - Automates UI emulator actions (search, view details, send direct messages, authentication) without manual screen clicking via endpoints (`/api/v1/apps/transform`, `/api/v1/apps/{package_name}/execute`).
  - Comprehensive unit test suite `tests/test_android_rpa_bridge.py` (572 total passed tests).

- **APK Function Converter & User API Profile Mapper (`aios_core/apk_converter.py`)**:
  - Converts Android APK exported components (Activities, Services, Receivers) into AIOS Capability instances, RBAC User API profiles, and API routes (`/api/v1/apk/convert`, `/api/v1/apk/profiles`).
  - Comprehensive unit test suite `tests/test_apk_converter.py` (570 total passed tests).

- **Milestone 9.0.3 Complete — Universal Multi-Species Ethics Framework (`aios_core/universal_multi_species_ethics.py`)**:
  - Multi-planetary ecological impact evaluation and biosphere non-disruption safety guarantees.
  - Comprehensive unit test suite `tests/test_universal_multi_species_ethics.py`.

- **Milestone 9.0.2 Complete — Bio-Digital Molecular DNA Runtime (`aios_core/molecular_dna_runtime.py`)**:
  - Translation of Constitutional Laws into synthetic DNA nucleotide sequences (A, T, C, G) with PCR molecule amplification simulation.
  - Comprehensive unit test suite `tests/test_molecular_dna_runtime.py`.

- **Milestone 9.0.1 Complete — Quantum Entangled Zero-Latency Communication Mesh (`aios_core/quantum_entanglement_mesh.py`)**:
  - Simulated EPR pair quantum teleportation channels with zero-latency state synchronization.
  - Comprehensive unit test suite `tests/test_quantum_entanglement_mesh.py` (567 total passed tests).

## [8.0.0-alpha] - 2026-07-21

### Added
- **Milestone 8.0.3 Complete — Cosmic Scale Swarm Matrix (`aios_core/cosmic_swarm_matrix.py`)**:
  - Light-speed delay vector compensation across inter-stellar nodes and holographic distributed memory shard state encoding.
  - Comprehensive unit test suite `tests/test_cosmic_swarm_matrix.py`.

- **Milestone 8.0.2 Complete — Self-Amending Infinite Constitutional Engine (`aios_core/infinite_constitution.py`)**:
  - Dynamic amendment synthesis with mathematical non-divergence alignment verification against core immutable axioms.
  - Comprehensive unit test suite `tests/test_infinite_constitution.py`.

- **Milestone 8.0.1 Complete — Universal Substrate-Agnostic Execution Engine (`aios_core/substrate_convergence.py`)**:
  - Substrate-agnostic task dispatching across Silicon, Photonic Optical, Neuromorphic SNN, Quantum QPU, and Bio-compute runtimes.
  - Comprehensive unit test suite `tests/test_substrate_convergence.py` (564 total passed tests).

## [7.0.0-alpha] - 2026-07-21

### Added
- **Milestone 7.0.3 Complete — Multi-Dimensional Universal World Model (`aios_core/multidimensional_world_model.py`)**:
  - Counterfactual predictive simulation engine forecasting system trajectories across CPU load, memory usage, economic cost, and system health.
  - Comprehensive unit test suite `tests/test_multidimensional_world_model.py`.

- **Milestone 7.0.2 Complete — Universal Constitutional Invariant Prover (`aios_core/universal_invariant_prover.py`)**:
  - Symbolic logic theorem prover evaluating state transition assertions against Constitutional invariants with SHA256 proof hashes.
  - Comprehensive unit test suite `tests/test_universal_invariant_prover.py`.

- **Milestone 7.0.1 Complete — Sovereign Recursive Self-Reflection Engine (`aios_core/sovereign_reflection.py`)**:
  - Metacognitive goal hierarchy auditor resolving belief contradictions and filtering malicious constitutional bypass attempts.
  - Comprehensive unit test suite `tests/test_sovereign_reflection.py` (561 total passed tests).

## [6.0.0-alpha] - 2026-07-21

### Added
- **Milestone 6.0.3 Complete — Planetary Mesh & Space Edge Orchestration (`aios_core/planetary_federation.py`)**:
  - Delay-Tolerant Network (DTN) mesh routing across terrestrial, orbital LEO satellites, and Lunar/deep space edge nodes.
  - Comprehensive unit test suite `tests/test_planetary_federation.py`.

- **Milestone 6.0.2 Complete — Autonomous Bio-Inspired Genetic Evolution Engine (`aios_core/biological_evolution.py`)**:
  - Chromosome genome encoding, single-point and uniform genetic crossover, Gaussian mutation, elitism survival selection, and constitutional integrity penalties.
  - Comprehensive unit test suite `tests/test_biological_evolution.py`.

- **Milestone 6.0.1 Complete — Neuromorphic Spiking Neural Network Matrix Engine (`aios_core/neuromorphic_matrix.py`)**:
  - Event-driven Leaky Integrate-and-Fire (LIF) spiking neuron arrays with membrane potential decay and spike firing reset.
  - Spike-Timing-Dependent Plasticity (STDP) unsupervised synaptic weight learning.
  - Comprehensive unit test suite `tests/test_neuromorphic_matrix.py` (558 total passed tests).

## [5.0.0-alpha] - 2026-07-21

### Added
- **Milestone 5.0.3 Complete — Quantum Native Computing & QAOA Engine (`aios_core/quantum_native.py`)**:
  - State vector Qubit simulator implementing Hadamard, CNOT, and measurement probabilities.
  - Quantum Approximate Optimization Algorithm (QAOA) solving NP-hard multi-agent task mapping graphs.
  - Comprehensive unit test suite `tests/test_quantum_native.py`.

- **Milestone 5.0.2 Complete — Global Swarm Governance & ZK Safety Proofs (`aios_core/global_swarm.py`)**:
  - W3C DID Node Identity protocol (`did:aios:<node_id>`) for inter-cluster federation.
  - Zero-Knowledge Safety Proofs (`ZeroKnowledgeSafetyProof`) ensuring zero-trust cross-cluster task verification without exposing secret task variables.
  - Byzantine Fault Tolerant (BFT) and Bayesian consensus voting engine for constitutional amendment proposals.
  - Comprehensive unit test suite `tests/test_global_swarm.py`.

- **Milestone 5.0.1 Complete — Real-Time Formal Code Verification Engine (`aios_core/formal_code_verifier.py`)**:
  - Abstract Syntax Tree (AST) AST-level static invariant proofs, infinite loop detection, reflection and dunder exploit blocking (`__subclasses__`, `__globals__`).
  - Pre/post-condition mathematical contract checking and import whitelist enforcement.
  - Comprehensive unit test suite `tests/test_formal_code_verifier.py` (549 total passed tests).

## [4.2.0-alpha] - 2026-07-21

### Added
- **Milestone 4.2.4 Complete — Enterprise Scaling & PostgreSQL Integration**:
  - Multi-dialect `Database` abstraction (`aios_core/storage.py`) handling transparent query translation between SQLite and PostgreSQL.
  - Kubernetes HorizontalPodAutoscaler template (`helm/aios/templates/hpa.yaml`) scaling based on target CPU/Memory metrics and task queue depth.
  - Comprehensive unit test suite `tests/test_storage_postgresql.py` (543 total passed tests).

- **Milestone 4.2.3 Complete — Official Web UI (React + TypeScript + Tailwind SPA)**:
  - Enterprise React SPA interface with tabbed views: Overview, Safety Dashboard, Agent Swarm Topology, Master Constitution (67 Articles), Knowledge Graph, and ML Model Registry.
  - Dedicated REST API endpoints in `aios_core/api/app.py`: `/api/v1/constitution`, `/api/v1/safety`, `/api/v1/knowledge-graph`, `/api/v1/agents`, `/api/v1/models`.
  - Comprehensive unit test suite `tests/test_web_ui_integration.py` (540 total passed tests).

- **Milestone 4.2.2 Complete — Production Hardening & Observability**:
  - `Telemetry` & OpenTelemetry metrics (`aios_core/telemetry.py`) with counters, gauges, histograms, and Prometheus exposition formatting.
  - `Tracer` W3C Trace Context propagation (`aios_core/tracing.py`) supporting `traceparent` (`00-{trace_id}-{span_id}-01`) headers, sub-spans, and thread-local context propagation.
  - `JSONFormatter` (`aios_core/logging_config.py`) for structured production logs enriched with `trace_id`, `span_id`, `agent_id`, and `constitutional_status`.
  - `BackupManager` (`aios_core/backup_manager.py`) with zero-downtime hot online SQLite snapshotting (`sqlite3.backup` API), SHA256 integrity validation, and retention policy cleaning.
  - Comprehensive unit test suites `tests/test_telemetry.py` and `tests/test_backup_manager.py` (535 total passed tests).

- **Milestone 4.2.1 Complete — Advanced ML Intelligence Layer**:
  - `ModelRegistry` (`aios_core/model_registry.py`) with artifact SHA256 hashing, stage promotion (`staging`, `production`), weight versioning, and evaluation metric logging.
  - `ModelServer` (`aios_core/model_serving.py`) with A/B traffic splitting, thread-safe inference, batch predictions, and latency tracking.
  - `AnomalyDetector` (`aios_core/anomaly_detection.py`) with Z-score and IQR statistical outlier detection for runtime metrics.
  - `PredictiveAutonomyRegulator` (`aios_core/predictive_autonomy.py`) dynamically risk-scoring agent plans and downgrading autonomy levels upon critical risk.
  - Comprehensive unit test suite `tests/test_ml_registry.py` (530 total passed tests).

## [4.1.0-alpha] - 2026-07-21

### Added
- **Constitutional Verification Tool (`tula`)** — autonomous tool (`tools/complete_constitution_tula.py`) for scanning articles I-LXVII, strict structure verification, compliance matrix generation, master index tracking, and report generation.
- **AI Safety & Ethics Test Suite** — comprehensive unit tests for safety layers, real-time safety monitor, dashboard, ethics evaluator, and benchmarks (`tests/test_ai_safety_framework.py`).
- **Cognition & Role Engine Test Suite** — unit tests for Theory of Mind, Emotional Intelligence, Metacognition, Social Intelligence, Creativity, AI Scientist, AI Researcher, AI Engineer, AI Product Manager, AI Startup (`tests/test_cognition_framework.py`).
- **Constitutional Verification Test Suite** — automated test suite for `tula` (`tests/test_tula.py`).
- Total test coverage expanded to **526 passed tests** (100% passing).

### Changed
- Unified versioning across `aios_core/__init__.py`, REST API `/health`, and tests to `4.1.0-alpha`.
- Fixed typing and compilation constraints in `ai_safety_evals.py` and `ai_safety_benchmark.py`.
- Updated `docs/constitution/COMPLIANCE_MATRIX.md`, `docs/constitution/INDEX.md`, and `docs/constitution/CONSTITUTION_REPORT.md` with full 67-article mapping.

## [4.0.0-alpha] - 2026-07-21

### Added
- **FederationManager** — multi-node coordination, task delegation, broadcast
- **MLPlannerScorer** — ML-enhanced plan scoring and optimization
- **MultiAgentOrchestrator** — dynamic team formation and conflict resolution
- **ConstitutionEvolver** — self-evolving constitution with automatic proposals
- **Web Dashboard** — real-time monitoring interface (Starlette)
- Full integration of all v4.0 subsystems into `Orchestrator`
- 20+ new tests for v4.0 components (total: 501 passing)

### Changed
- `Orchestrator.stats()` now includes `federation`, `ml_scorer`, `multi_agent`, `constitution_evolver`
- Enhanced autonomy with automatic level adjustment
- Improved monitoring (`/metrics`, `monitor.py`)

### Infrastructure
- Docker + docker-compose support
- Prometheus-compatible metrics
- Production-ready deployment files

## [3.1.0] - 2026-07-21

### Added
- Enhanced monitoring and health endpoints
- Docker support
- 485+ tests

## [3.0.0] - 2026-07-19

Initial stable release with full constitution (67 articles), orchestrator, evolution, and API layers.

---

**Next milestone:** v4.1 (Kubernetes operator, official SDK, capability marketplace)
