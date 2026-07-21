# AIOS Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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