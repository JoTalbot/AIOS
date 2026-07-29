# AIOS 11.3.0 — Release Notes

**Date:** 2026-07-29
**Type:** Feature release (closes the two remaining unchecked roadmap items from v10.17.0) + CI hardening window.

---

## Highlights

### 1. Agent Memory Optimization (Vector compression)

Roadmap item *"Implement Agent Memory Optimization (Vector compression)"* — done.

New module `aios_core/memory_compression.py`:

- **`HashingVectorizer`** — dependency-free deterministic text → 512d dense vector
  (signed hashing trick + L2 normalisation). No vocabulary, stable across processes.
- **`VectorCompressor`** — Johnson–Lindenstrauss random projection (deterministic
  Achlioptas ±1 matrix) 512d → 64d, then per-vector affine scalar quantisation to uint8.
  - Storage: 4096 B → **80 B per vector (~51×)**
  - Cosine geometry is preserved in compressed space — top-1 recall holds on memory-sized corpora (tested).
- Serialized blobs: `pack_compressed()` / `unpack_compressed()`, dict round-trip support.

`AgentMemorySystem` integration:

- `optimize_storage(target_dim=64)` — builds/rebuilds the compressed index for long-term + episodic pools, returns a byte-savings report.
- `recall_compressed(query, top_k=5, pool=...)` — similarity recall entirely in compressed space.
- `compression_stats()` + `stats()["compression"]` exposure.

### 2. Substrate Convergence Dashboard UI (live)

Roadmap item *"Introduce Substrate Convergence Dashboard UI"* — done.

The page at `dashboard/substrate.html` was a pretty but self-animating mock
(fake timers, fake health jitter). It is now a real dashboard:

- `GET /substrate` serves the page.
- Live endpoints backed by a shared `SubstrateConvergenceEngine`:
  - `GET /api/substrate/stats` — dispatches, queue depth, energy cost, failover counters
  - `GET /api/substrate/mesh` — per-substrate latency/efficiency/load/health/active
  - `GET /api/substrate/energy` — energy accounting + efficiency ranking
  - `GET /api/substrate/history?limit=N` — recent real routing decisions (N ≤ 200, validated)
- The page polls all three data sources every 5 s; connection state is shown in the header.

### Tests

- `tests/test_memory_compression.py` — 18 tests (determinism, geometry preservation, top-1 recall, quantisation edge cases, pack/dict round-trips, AgentMemorySystem integration).
- `tests/test_substrate_dashboard.py` — 6 tests (page, stats shape, five-substrate mesh, energy ranking, history lifecycle, limit validation).

**Full suite: ~3985 tests, 0 failures.** Ruff: 0 errors, format clean.

---

## CI/Infra window (included in this release)

- 100% green GitHub Actions board on one commit (21/21 check-runs).
- Coverage workflow installs full `requirements.txt` (was `.[dev]` only → jinja2/numpy collection errors).
- Docker/Trivy: GHCR lowercase image reference; `security-events: write` for SARIF upload.
- Deploy workflows (`deploy.yml`, `deploy-aws.yml`, full-ci deploy job) auto-skip green when infra secrets are absent (`DOCKERHUB_*`/`VPS_*`, `AWS_ROLE_ARN` repo variable, `SSH_PRIVATE_KEY`/`SSH_KNOWN_HOSTS`).
- Full CI/CD: KVM udev rule (x86_64 emulators boot), AVD config.ini appended (not overwritten), `ANDROID_HOME` pinned to the custom SDK root, system-image id uses `;` separators, GA-verify matches the real `simulation` report schema.
- Emulator calibration chain (`setup-emulators`, `calibrate-platforms`, `integration-tests`) runs on manual `workflow_dispatch` only (jobs cannot share emulator state across runners; needs live APKs).
- Stale `gt/*` + `convoy/*` bot branches deleted; `delete_branch_on_merge` enabled repo-side.

## Upgrade notes

- No breaking changes. New endpoints/dashboard are additive; `AgentMemorySystem` API is backward compatible (new methods only).
- Requirements: no new dependencies (compression uses numpy, already required).
