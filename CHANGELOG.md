# AIOS Changelog

All notable changes to this project will be documented in this file.

## [4.2.0-alpha] - In Progress (2026-07-21)

### Added
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